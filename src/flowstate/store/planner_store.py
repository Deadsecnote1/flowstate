# SPDX-License-Identifier: GPL-3.0-or-later
"""Daily planner persistence."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from flowstate.store.base import (
    Observable,
    atomic_write_json,
    read_json_with_status,
    resolve_data_dir,
)

RepeatMode = Literal["none", "daily"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PlanTask:
    id: str
    title: str
    date: str  # YYYY-MM-DD
    start_min: int = 9 * 60  # minutes from midnight
    end_min: int = 10 * 60
    all_day: bool = False
    notes: str = ""
    completed: bool = False
    repeat: RepeatMode = "none"
    color: str = "coral"  # coral | blue | green
    created_at: str = field(default_factory=_utc_now)
    client_updated_at: str = field(default_factory=_utc_now)
    deleted_at: str | None = None

    @staticmethod
    def create(
        title: str,
        day: date,
        start_min: int = 9 * 60,
        end_min: int = 10 * 60,
    ) -> PlanTask:
        now = _utc_now()
        return PlanTask(
            id=str(uuid.uuid4()),
            title=title.strip() or "New task",
            date=day.isoformat(),
            start_min=start_min,
            end_min=max(end_min, start_min + 1),
            created_at=now,
            client_updated_at=now,
        )

    @property
    def duration_min(self) -> int:
        return max(1, self.end_min - self.start_min)


def _occurrence_id(virtual_id: str) -> str:
    # The same series and date must map to the same UUID on every device.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"urn:flowstate:{virtual_id}"))


class PlannerStore(Observable):
    def __init__(
        self,
        app_id: str = "io.github.Deadsecnote1.Flowstate",
        data_dir: Path | None = None,
    ) -> None:
        super().__init__()
        if data_dir is None:
            data_dir = resolve_data_dir(app_id)
        else:
            data_dir.mkdir(parents=True, exist_ok=True)
        self._path = data_dir / "planner.json"
        self._tasks: list[PlanTask] = []
        self._inbox: list[dict] = []
        self._sync_hook: Callable[[str, str], None] | None = None
        self.load_error: str | None = None
        self.load()
        if not self._tasks and self.load_error is None and not self._path.exists():
            self._seed_defaults()
        elif not self._tasks and self.load_error is not None:
            self._seed_defaults()

    def set_sync_hook(self, hook: Callable[[str, str], None] | None) -> None:
        self._sync_hook = hook

    def _emit_sync(self, kind: str, item_id: str) -> None:
        if self._sync_hook:
            self._sync_hook(kind, item_id)

    def _touch_task(self, task: PlanTask) -> None:
        task.client_updated_at = _utc_now()

    def _touch_inbox(self, item: dict) -> None:
        item["client_updated_at"] = _utc_now()

    def load(self) -> None:
        self.load_error = None
        raw, ok = read_json_with_status(self._path, {"tasks": [], "inbox": []})
        self._tasks = []
        self._inbox = []
        if not ok:
            self.load_error = "planner.json was corrupt or unreadable"
            self._quarantine_corrupt(self._path)
            return
        try:
            for item in raw.get("tasks", []):
                item.setdefault("repeat", "none")
                item.setdefault("color", "coral")
                item.setdefault("client_updated_at", item.get("created_at") or _utc_now())
                item.setdefault("deleted_at", None)
                self._tasks.append(PlanTask(**item))
            for item in raw.get("inbox", []):
                item.setdefault("client_updated_at", _utc_now())
                item.setdefault("deleted_at", None)
                self._inbox.append(item)
        except (AttributeError, TypeError, KeyError, ValueError):
            self.load_error = "planner.json had invalid entries"
            self._tasks = []
            self._inbox = []
            self._quarantine_corrupt(self._path)

    @staticmethod
    def _quarantine_corrupt(path: Path) -> None:
        if not path.exists():
            return
        try:
            backup = path.with_name(path.name + ".bak")
            path.replace(backup)
        except OSError:
            pass

    def save(self) -> None:
        payload = {
            "tasks": [asdict(t) for t in self._tasks],
            "inbox": self._inbox,
        }
        atomic_write_json(self._path, payload)

    def _active_tasks(self) -> list[PlanTask]:
        return [t for t in self._tasks if not t.deleted_at]

    def _seed_defaults(self) -> None:
        today = date.today().isoformat()
        self._tasks = [
            PlanTask(
                id=str(uuid.uuid4()),
                title="Wake up",
                date=today,
                start_min=8 * 60,
                end_min=8 * 60 + 1,
                repeat="daily",
                color="coral",
            ),
            PlanTask(
                id=str(uuid.uuid4()),
                title="Go to bed",
                date=today,
                start_min=22 * 60,
                end_min=22 * 60 + 1,
                repeat="daily",
                color="blue",
            ),
        ]
        self.save()

    def tasks_for_day(self, day: date) -> list[PlanTask]:
        key = day.isoformat()
        result: list[PlanTask] = []
        stored_ids = {task.id for task in self._tasks}
        active = self._active_tasks()
        series = [task for task in active if task.repeat == "daily" and task.date < key]
        linked_ids = {_occurrence_id(f"virt-{task.id}-{key}") for task in series}
        legacy_slots = {
            (task.title, task.start_min) for task in active
            if task.date == key and task.repeat == "none" and task.id not in linked_ids
        }
        for task in active:
            if task.date == key:
                result.append(task)
            elif task.repeat == "daily" and task.date <= key:
                virtual_id = f"virt-{task.id}-{key}"
                if (_occurrence_id(virtual_id) not in stored_ids
                        and (task.title, task.start_min) not in legacy_slots):
                    result.append(replace(
                        task, id=virtual_id, date=key, completed=False,
                    ))
        result.sort(key=lambda t: (t.all_day, t.start_min, t.title))
        return result

    def get(self, task_id: str) -> PlanTask | None:
        for task in self._active_tasks():
            if task.id == task_id:
                return task
        return None

    def get_sync_task(self, task_id: str) -> PlanTask | None:
        if task_id.startswith("virt-"):
            return None
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    def iter_sync_tasks(self) -> list[PlanTask]:
        return [t for t in self._tasks if not t.id.startswith("virt-")]

    def iter_sync_inbox_ids(self) -> list[str]:
        # Include tombstones so deletes are pushed on full-snapshot sync.
        return [str(i.get("id")) for i in self._inbox if i.get("id")]

    def get_sync_inbox(self, item_id: str) -> dict | None:
        for item in self._inbox:
            if str(item.get("id")) == item_id:
                return item
        return None

    def add(self, task: PlanTask, *, inbox_id: str | None = None) -> PlanTask:
        item = self.get_sync_inbox(inbox_id) if inbox_id is not None else None
        if item is not None and not item.get("deleted_at"):
            item["deleted_at"] = _utc_now()
            self._touch_inbox(item)
        self._tasks.append(task)
        self.save()
        self._emit_sync("planner_task", task.id)
        if item is not None:
            self._emit_sync("inbox", str(item["id"]))
        self._notify()
        return task

    def update(self, task: PlanTask) -> None:
        if task.id.startswith("virt-"):
            task = replace(task, id=_occurrence_id(task.id), repeat="none", created_at=_utc_now())
            self._touch_task(task)
            if self.get_sync_task(task.id) is None:
                self.add(task)
                return
        for i, existing in enumerate(self._tasks):
            if existing.id == task.id:
                task.client_updated_at = _utc_now()
                self._tasks[i] = task
                self.save()
                self._emit_sync("planner_task", task.id)
                self._notify()
                return

    def remove(self, task_id: str) -> None:
        if task_id.startswith("virt-"):
            return
        task = self.get_sync_task(task_id)
        if task is None or task.deleted_at:
            return
        task.deleted_at = _utc_now()
        self._touch_task(task)
        self.save()
        self._emit_sync("planner_task", task.id)
        self._notify()

    def toggle_complete(self, task_id: str) -> None:
        task = self.get(task_id)
        if task is None and task_id.startswith("virt-"):
            day = date.fromisoformat(task_id[-10:])
            task = next((t for t in self.tasks_for_day(day) if t.id == task_id), None)
        if task is None:
            return
        self.update(replace(task, completed=not task.completed))

    def add_inbox(self, title: str) -> None:
        title = title.strip()
        if not title:
            return
        item = {
            "id": str(uuid.uuid4()),
            "title": title,
            "client_updated_at": _utc_now(),
            "deleted_at": None,
        }
        self._inbox.insert(0, item)
        self.save()
        self._emit_sync("inbox", item["id"])
        self._notify()

    @property
    def inbox(self) -> list[dict]:
        return [i for i in self._inbox if not i.get("deleted_at")]

    def remove_inbox(self, item_id: str) -> None:
        for item in self._inbox:
            if str(item.get("id")) == item_id and not item.get("deleted_at"):
                item["deleted_at"] = _utc_now()
                self._touch_inbox(item)
                self.save()
                self._emit_sync("inbox", item_id)
                self._notify()
                return

    def apply_remote_task(self, row: dict) -> bool:
        from flowstate.sync.merge import remote_is_newer

        task_id = str(row.get("id", ""))
        if not task_id or task_id.startswith("virt-"):
            return False
        existing = self.get_sync_task(task_id)
        if existing and not remote_is_newer(existing.client_updated_at, row):
            return False
        task = PlanTask(
            id=task_id,
            title=str(row.get("title", "")),
            date=str(row.get("task_date", date.today().isoformat())),
            start_min=int(row.get("start_min", 540)),
            end_min=int(row.get("end_min", 600)),
            all_day=bool(row.get("all_day", False)),
            notes=str(row.get("notes", "")),
            completed=bool(row.get("completed", False)),
            repeat=row.get("repeat", "none") or "none",
            color=row.get("color", "coral") or "coral",
            created_at=str(row.get("created_at") or _utc_now()),
            client_updated_at=str(row.get("client_updated_at") or _utc_now()),
            deleted_at=row.get("deleted_at"),
        )
        if existing:
            index = self._tasks.index(existing)
            self._tasks[index] = task
        else:
            self._tasks.append(task)
        self.save()
        return True

    def apply_remote_inbox(self, row: dict) -> bool:
        from flowstate.sync.merge import remote_is_newer

        item_id = str(row.get("id", ""))
        if not item_id:
            return False
        existing = self.get_sync_inbox(item_id)
        local_ts = str(existing.get("client_updated_at", "")) if existing else ""
        if existing and not remote_is_newer(local_ts, row):
            return False
        item = {
            "id": item_id,
            "title": str(row.get("title", "")),
            "client_updated_at": str(row.get("client_updated_at") or _utc_now()),
            "deleted_at": row.get("deleted_at"),
        }
        if existing:
            index = self._inbox.index(existing)
            self._inbox[index] = item
        else:
            self._inbox.append(item)
        self.save()
        return True
