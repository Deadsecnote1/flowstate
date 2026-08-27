# SPDX-License-Identifier: GPL-3.0-or-later
"""Daily planner persistence."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

from gi.repository import GLib

from flowstate.store.base import (
    Observable,
    atomic_write_json,
    read_json_with_status,
    resolve_data_dir,
)

RepeatMode = Literal["none", "daily"]


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
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @staticmethod
    def create(
        title: str,
        day: date,
        start_min: int = 9 * 60,
        end_min: int = 10 * 60,
    ) -> PlanTask:
        return PlanTask(
            id=str(uuid.uuid4()),
            title=title.strip() or "New task",
            date=day.isoformat(),
            start_min=start_min,
            end_min=max(end_min, start_min + 1),
        )

    @property
    def duration_min(self) -> int:
        return max(1, self.end_min - self.start_min)


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
        self.load_error: str | None = None
        self.load()
        if not self._tasks and self.load_error is None and not self._path.exists():
            self._seed_defaults()
        elif not self._tasks and self.load_error is not None:
            # Corrupt file already quarantined; seed a usable default planner.
            self._seed_defaults()

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
                self._tasks.append(PlanTask(**item))
            self._inbox = list(raw.get("inbox", []))
        except (TypeError, KeyError, ValueError):
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
        for task in self._tasks:
            if task.date == key:
                result.append(task)
            elif task.repeat == "daily" and task.date <= key:
                # Show daily recurring tasks on later days as virtual copies
                # unless an override exists same title+time that day
                exists = any(
                    t.date == key
                    and t.title == task.title
                    and t.start_min == task.start_min
                    for t in self._tasks
                )
                if not exists:
                    clone = PlanTask(
                        id=f"virt-{task.id}-{key}",
                        title=task.title,
                        date=key,
                        start_min=task.start_min,
                        end_min=task.end_min,
                        all_day=task.all_day,
                        notes=task.notes,
                        completed=False,
                        repeat="daily",
                        color=task.color,
                        created_at=task.created_at,
                    )
                    result.append(clone)
        result.sort(key=lambda t: (t.all_day, t.start_min, t.title))
        return result

    def get(self, task_id: str) -> PlanTask | None:
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    def add(self, task: PlanTask) -> PlanTask:
        self._tasks.append(task)
        self.save()
        self._notify()
        return task

    def update(self, task: PlanTask) -> None:
        if task.id.startswith("virt-"):
            # Materialize virtual daily instance
            real = PlanTask(
                id=str(uuid.uuid4()),
                title=task.title,
                date=task.date,
                start_min=task.start_min,
                end_min=task.end_min,
                all_day=task.all_day,
                notes=task.notes,
                completed=task.completed,
                repeat="none",
                color=task.color,
            )
            self._tasks.append(real)
            self.save()
            self._notify()
            return
        for i, existing in enumerate(self._tasks):
            if existing.id == task.id:
                self._tasks[i] = task
                self.save()
                self._notify()
                return

    def remove(self, task_id: str) -> None:
        if task_id.startswith("virt-"):
            return
        self._tasks = [t for t in self._tasks if t.id != task_id]
        self.save()
        self._notify()

    def toggle_complete(self, task_id: str) -> None:
        task = self.get(task_id)
        if not task:
            return
        task.completed = not task.completed
        self.save()
        self._notify()

    def add_inbox(self, title: str) -> None:
        title = title.strip()
        if not title:
            return
        self._inbox.insert(0, {"id": str(uuid.uuid4()), "title": title})
        self.save()
        self._notify()

    @property
    def inbox(self) -> list[dict]:
        return list(self._inbox)

    def remove_inbox(self, item_id: str) -> None:
        self._inbox = [i for i in self._inbox if i.get("id") != item_id]
        self.save()
        self._notify()
