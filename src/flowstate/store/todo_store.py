# SPDX-License-Identifier: GPL-3.0-or-later
"""Todo list persistence with optional archive partition."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from flowstate.store.base import (
    Observable,
    atomic_write_json,
    read_json,
    read_json_with_status,
    resolve_data_dir,
)

FilterMode = Literal["all", "active", "completed"]


@dataclass
class TodoItem:
    id: str
    title: str
    completed: bool = False
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    notes: str = ""

    @staticmethod
    def create(title: str) -> TodoItem:
        return TodoItem(id=str(uuid.uuid4()), title=title.strip())


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
        self.load_error: str | None = None
        self.load()

    def load(self) -> None:
        self.load_error = None
        raw, ok = read_json_with_status(self._path, {"items": []})
        if not ok:
            self.load_error = "todos.json was corrupt or unreadable"
            self._items = []
            self._quarantine_corrupt(self._path)
            return
        try:
            self._items = [TodoItem(**item) for item in raw.get("items", [])]
        except (TypeError, KeyError, ValueError):
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

    @property
    def items(self) -> list[TodoItem]:
        return list(self._items)

    def filtered(
        self,
        mode: FilterMode = "all",
        query: str = "",
    ) -> list[TodoItem]:
        q = query.strip().lower()
        result = self._items
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
        total = len(self._items)
        completed = sum(1 for i in self._items if i.completed)
        return total, total - completed, completed

    def add(self, title: str) -> TodoItem | None:
        title = title.strip()
        if not title:
            return None
        item = TodoItem.create(title)
        self._items.insert(0, item)
        self.save()
        self._notify()
        return item

    def toggle(self, item_id: str) -> None:
        for item in self._items:
            if item.id == item_id:
                item.completed = not item.completed
                self.save()
                self._notify()
                return

    def update_title(self, item_id: str, title: str) -> None:
        title = title.strip()
        if not title:
            return
        for item in self._items:
            if item.id == item_id:
                item.title = title
                self.save()
                self._notify()
                return

    def remove(self, item_id: str) -> None:
        self._items = [i for i in self._items if i.id != item_id]
        self.save()
        self._notify()

    def clear_completed(self) -> int:
        """Permanently delete completed tasks."""
        before = len(self._items)
        self._items = [i for i in self._items if not i.completed]
        removed = before - len(self._items)
        if removed:
            self.save()
            self._notify()
        return removed

    def archive_completed(self) -> int:
        """Move completed tasks to todos_archive.json and remove from active list."""
        archived = [i for i in self._items if i.completed]
        if not archived:
            return 0
        self._save_archive(archived)
        self._items = [i for i in self._items if not i.completed]
        self.save()
        self._notify()
        return len(archived)
