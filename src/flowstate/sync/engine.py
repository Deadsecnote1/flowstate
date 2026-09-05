# SPDX-License-Identifier: GPL-3.0-or-later
"""Bidirectional sync engine: push queue, pull deltas, merge."""

from __future__ import annotations

import threading
from typing import Callable

from flowstate.store.planner_store import PlannerStore, PlanTask
from flowstate.store.todo_store import TodoStore, TodoItem
from flowstate.sync.auth import AuthError, sign_in_with_google, sign_out
from flowstate.sync.client import SyncClient, SyncClientError, supabase_available
from flowstate.sync.config import is_sync_configured
from flowstate.sync.queue import QueueEntry, SyncQueue
from flowstate.sync.state import SyncSession, SyncStateStore
from flowstate.sync.timeutil import delta_since, parse_iso, utc_now_iso


class SyncEngine:
    """Coordinates auth, outbound queue, and delta pull for todo + planner data."""

    def __init__(
        self,
        todo_store: TodoStore,
        planner_store: PlannerStore,
    ) -> None:
        self.todo_store = todo_store
        self.planner_store = planner_store
        self._state = SyncStateStore()
        self._queue = SyncQueue(todo_store._path.parent)  # noqa: SLF001
        self._lock = threading.Lock()
        self._status = "Not signed in"
        self._listeners: list[Callable[[], None]] = []
        self._auto_sync_timer: threading.Timer | None = None

        todo_store.set_sync_hook(self._on_todo_change)
        planner_store.set_sync_hook(self._on_planner_change)

    def set_status_listener(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def _set_status(self, text: str) -> None:
        self._status = text
        for listener in list(self._listeners):
            listener()

    @property
    def status_text(self) -> str:
        return self._status

    def is_available(self) -> bool:
        return is_sync_configured() and supabase_available()

    def is_signed_in(self) -> bool:
        return self._state.is_signed_in()

    def session_email(self) -> str:
        session = self._state.load_session()
        return session.email if session else ""

    def _on_todo_change(self, item_id: str) -> None:
        self._queue.enqueue("task", item_id)
        self.schedule_auto_sync()

    def _on_planner_change(self, kind: str, item_id: str) -> None:
        if kind == "inbox":
            self._queue.enqueue("inbox_item", item_id)
        else:
            self._queue.enqueue("planner_task", item_id)
        self.schedule_auto_sync()

    def schedule_auto_sync(self, delay_seconds: float = 2.0) -> None:
        """Debounced background sync after local edits."""
        if not self.is_available() or not self.is_signed_in():
            return
        if self._auto_sync_timer is not None:
            self._auto_sync_timer.cancel()
        self._auto_sync_timer = threading.Timer(delay_seconds, self._auto_sync_tick)
        self._auto_sync_timer.daemon = True
        self._auto_sync_timer.start()

    def _auto_sync_tick(self) -> None:
        self._auto_sync_timer = None
        self.run_sync_async(on_done=self._notify_status_listeners)

    def _notify_status_listeners(self, _msg: str) -> None:
        for listener in list(self._listeners):
            listener()

    def sign_in(self, on_progress: Callable[[str], None] | None = None) -> SyncSession:
        session = sign_in_with_google(on_progress=on_progress)
        self._set_status(f"Signed in as {session.email or session.user_id}")
        self.run_sync(on_progress=on_progress)
        return session

    def sign_in_async(self, on_done: Callable[[str], None] | None = None) -> None:
        def worker() -> None:
            try:
                session = self.sign_in()
                msg = f"Signed in as {session.email or session.user_id}"
            except AuthError as exc:
                msg = str(exc)
                self._set_status(msg)
            except Exception as exc:  # pragma: no cover
                msg = f"Sign-in failed: {exc}"
                self._set_status(msg)
            if on_done:
                from gi.repository import GLib

                GLib.idle_add(on_done, msg)

        threading.Thread(target=worker, daemon=True).start()

    def sign_out_user(self) -> None:
        sign_out()
        self._set_status("Signed out")

    def run_sync(self, on_progress: Callable[[str], None] | None = None) -> str:
        if not self.is_available():
            msg = "Sync not configured"
            self._set_status(msg)
            return msg
        if not self.is_signed_in():
            msg = "Not signed in"
            self._set_status(msg)
            return msg

        with self._lock:
            try:
                if on_progress:
                    on_progress("Syncing…")
                client = SyncClient(state=self._state)
                session = client.restore_session()
                if session is None:
                    msg = "Session expired — sign in again"
                    self._set_status(msg)
                    return msg
                # Pull first so remote tombstones/edits land locally before we
                # upsert. Otherwise a stale live row can overwrite a newer delete.
                pulled = self._pull(client)
                pushed = self._push(client, session.user_id)
                now = utc_now_iso()
                self._state.save_last_sync_at(now)
                msg = f"Synced ({pulled} pulled, {pushed} pushed)"
                self._set_status(msg)
                return msg
            except SyncClientError as exc:
                msg = str(exc)
                self._set_status(msg)
                return msg
            except Exception as exc:  # pragma: no cover - network errors
                msg = f"Sync failed: {exc}"
                self._set_status(msg)
                return msg

    def run_sync_async(
        self,
        on_done: Callable[[str], None] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        def worker() -> None:
            result = self.run_sync(on_progress=on_progress)
            if on_done:
                from gi.repository import GLib

                GLib.idle_add(on_done, result)

        threading.Thread(target=worker, daemon=True).start()

    def _push(self, client: SyncClient, user_id: str) -> int:
        entries = self._queue.drain()
        if not entries:
            for item in self.todo_store.iter_sync_items():
                entries.append(QueueEntry.upsert("task", item.id))
            for task in self.planner_store.iter_sync_tasks():
                entries.append(QueueEntry.upsert("planner_task", task.id))
            for inbox_id in self.planner_store.iter_sync_inbox_ids():
                entries.append(QueueEntry.upsert("inbox_item", inbox_id))

        task_rows: list[dict] = []
        planner_rows: list[dict] = []
        inbox_rows: list[dict] = []
        seen: set[tuple[str, str]] = set()

        for entry in entries:
            key = (entry.entity, entry.entity_id)
            if key in seen:
                continue
            seen.add(key)

            if entry.entity == "task":
                item = self.todo_store.get_sync_item(entry.entity_id)
                if item:
                    task_rows.append(_task_to_row(item, user_id))
            elif entry.entity == "planner_task":
                task = self.planner_store.get_sync_task(entry.entity_id)
                if task:
                    planner_rows.append(_planner_to_row(task, user_id))
            elif entry.entity == "inbox_item":
                row = self.planner_store.get_sync_inbox(entry.entity_id)
                if row:
                    inbox_rows.append(_inbox_to_row(row, user_id))

        try:
            client.upsert_rows("tasks", task_rows)
            client.upsert_rows("planner_tasks", planner_rows)
            client.upsert_rows("inbox_items", inbox_rows)
        except Exception:
            for entry in entries:
                self._queue.enqueue(entry.entity, entry.entity_id)
            raise
        return len(task_rows) + len(planner_rows) + len(inbox_rows)

    def _pull(self, client: SyncClient) -> int:
        since = delta_since(self._state.load_last_sync_at())
        count = 0
        for row in client.fetch_since("tasks", since):
            if self.todo_store.apply_remote_task(row):
                count += 1
        for row in client.fetch_since("planner_tasks", since):
            if self.planner_store.apply_remote_task(row):
                count += 1
        for row in client.fetch_since("inbox_items", since):
            if self.planner_store.apply_remote_inbox(row):
                count += 1
        if count:
            self.todo_store._notify()  # noqa: SLF001
            self.planner_store._notify()  # noqa: SLF001
        return count


def _task_to_row(item: TodoItem, user_id: str) -> dict:
    return {
        "id": item.id,
        "user_id": user_id,
        "title": item.title,
        "completed": item.completed,
        "notes": item.notes,
        "created_at": item.created_at,
        "client_updated_at": item.client_updated_at,
        "deleted_at": item.deleted_at,
    }


def _planner_to_row(task: PlanTask, user_id: str) -> dict:
    return {
        "id": task.id,
        "user_id": user_id,
        "title": task.title,
        "task_date": task.date,
        "start_min": task.start_min,
        "end_min": task.end_min,
        "all_day": task.all_day,
        "notes": task.notes,
        "completed": task.completed,
        "repeat": task.repeat,
        "color": task.color,
        "created_at": task.created_at,
        "client_updated_at": task.client_updated_at,
        "deleted_at": task.deleted_at,
    }


def _inbox_to_row(row: dict, user_id: str) -> dict:
    return {
        "id": row["id"],
        "user_id": user_id,
        "title": row["title"],
        "client_updated_at": row.get("client_updated_at") or utc_now_iso(),
        "deleted_at": row.get("deleted_at"),
    }
