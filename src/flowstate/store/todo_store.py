# SPDX-License-Identifier: GPL-3.0-or-later
"""Todo list persistence with optional archive partition."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Literal

from flowstate.store.base import (
    Observable,
    atomic_write_json,
    read_json,
    read_json_with_status,
    resolve_data_dir,
)

FilterMode = Literal["all", "active", "completed"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TodoItem:
    id: str
    title: str
    completed: bool = False
    created_at: str = field(default_factory=_utc_now)
    notes: str = ""
    client_updated_at: str = field(default_factory=_utc_now)
    deleted_at: str | None = None

    @staticmethod
    def create(title: str) -> TodoItem:
        now = _utc_now()
        return TodoItem(
            id=str(uuid.uuid4()),
            title=title.strip(),
            created_at=now,
            client_updated_at=now,
        )


class TodoStore(Observable):
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
        self._path = data_dir / "todos.json"
        self._archive_path = data_dir / "todos_archive.json"
        self._items: list[TodoItem] = []
        self._sync_hook: Callable[[str], None] | None = None
        self.load_error: str | None = None
        self.load()

    def set_sync_hook(self, hook: Callable[[str], None] | None) -> None:
        self._sync_hook = hook

    def _emit_sync(self, item_id: str) -> None:
        if self._sync_hook:
            self._sync_hook(item_id)

    def _touch(self, item: TodoItem) -> None:
        item.client_updated_at = _utc_now()

    def _find_raw(self, item_id: str) -> TodoItem | None:
        for item in self._items:
            if item.id == item_id:
                return item
        return None

    def load(self) -> None:
        self.load_error = None
        raw, ok = read_json_with_status(self._path, {"items": []})
        if not ok:
            self.load_error = "todos.json was corrupt or unreadable"
            self._items = []
            self._quarantine_corrupt(self._path)
            return
        try:
            items: list[TodoItem] = []
            for entry in raw.get("items", []):
                entry.setdefault("client_updated_at", entry.get("created_at") or _utc_now())
                entry.setdefault("deleted_at", None)
                items.append(TodoItem(**entry))
            self._items = items
        except (AttributeError, TypeError, KeyError, ValueError):
            self.load_error = "todos.json had invalid task entries"
            self._items = []
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
        atomic_write_json(self._path, {"items": [asdict(item) for item in self._items]})

    def _save_archive(self, archived: list[TodoItem]) -> None:
        existing = read_json(self._archive_path, {"items": []})
        items = list(existing.get("items", []))
        items.extend(asdict(item) for item in archived)
        atomic_write_json(self._archive_path, {"items": items})

    def _active_items(self) -> list[TodoItem]:
        return [i for i in self._items if not i.deleted_at]

    @property
    def items(self) -> list[TodoItem]:
        return list(self._active_items())

    def iter_sync_items(self) -> list[TodoItem]:
        return list(self._items)

    def get_sync_item(self, item_id: str) -> TodoItem | None:
        return self._find_raw(item_id)

    def filtered(
        self,
        mode: FilterMode = "all",
        query: str = "",
    ) -> list[TodoItem]:
        q = query.strip().lower()
        result = self._active_items()
        if mode == "active":
            result = [i for i in result if not i.completed]
        elif mode == "completed":
            result = [i for i in result if i.completed]
        if q:
            result = [
                i for i in result if q in i.title.lower() or q in i.notes.lower()
            ]
        return result

    def counts(self) -> tuple[int, int, int]:
        active = self._active_items()
        total = len(active)
        completed = sum(1 for i in active if i.completed)
        return total, total - completed, completed

    def add(self, title: str) -> TodoItem | None:
        title = title.strip()
        if not title:
            return None
        item = TodoItem.create(title)
        self._items.insert(0, item)
        self.save()
        self._emit_sync(item.id)
        self._notify()
        return item

    def toggle(self, item_id: str) -> None:
        item = self._find_raw(item_id)
        if item is None or item.deleted_at:
            return
        item.completed = not item.completed
        self._touch(item)
        self.save()
        self._emit_sync(item.id)
        self._notify()

    def update_title(self, item_id: str, title: str) -> None:
        title = title.strip()
        if not title:
            return
        item = self._find_raw(item_id)
        if item is None or item.deleted_at:
            return
        item.title = title
        self._touch(item)
        self.save()
        self._emit_sync(item.id)
        self._notify()

    def remove(self, item_id: str) -> None:
        item = self._find_raw(item_id)
        if item is None or item.deleted_at:
            return
        item.deleted_at = _utc_now()
        self._touch(item)
        self.save()
        self._emit_sync(item.id)
        self._notify()

    def clear_completed(self) -> int:
        """Soft-delete all completed tasks (sync tombstones)."""
        removed = 0
        now = _utc_now()
        for item in self._items:
            if item.deleted_at or not item.completed:
                continue
            item.deleted_at = now
            self._touch(item)
            self._emit_sync(item.id)
            removed += 1
        if removed:
            self.save()
            self._notify()
        return removed

    def archive_completed(self) -> int:
        """Move completed tasks to todos_archive.json and tombstone active copies."""
        archived = [i for i in self._active_items() if i.completed]
        if not archived:
            return 0
        self._save_archive(archived)
        now = _utc_now()
        for item in archived:
            item.deleted_at = now
            self._touch(item)
            self._emit_sync(item.id)
        self.save()
        self._notify()
        return len(archived)

    def apply_remote_task(self, row: dict) -> bool:
        from flowstate.sync.merge import remote_is_newer

        item_id = str(row.get("id", ""))
        if not item_id:
            return False
        existing = self._find_raw(item_id)
        if existing and not remote_is_newer(existing.client_updated_at, row):
            return False
        item = TodoItem(
            id=item_id,
            title=str(row.get("title", "")),
            completed=bool(row.get("completed", False)),
            notes=str(row.get("notes", "")),
            created_at=str(row.get("created_at") or _utc_now()),
            client_updated_at=str(row.get("client_updated_at") or _utc_now()),
            deleted_at=row.get("deleted_at"),
        )
        if existing:
            index = self._items.index(existing)
            self._items[index] = item
        else:
            self._items.append(item)
        self.save()
        return True
