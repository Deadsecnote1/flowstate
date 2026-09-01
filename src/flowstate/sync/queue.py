# SPDX-License-Identifier: GPL-3.0-or-later
"""Durable outbound sync queue (survives app restarts)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from flowstate.settings import APP_ID
from flowstate.store.base import atomic_write_json, read_json, resolve_data_dir
from flowstate.sync.timeutil import utc_now_iso

EntityKind = Literal["task", "planner_task", "inbox_item"]
QueueOp = Literal["upsert", "delete"]


@dataclass
class QueueEntry:
    entity: EntityKind
    entity_id: str
    op: QueueOp
    queued_at: str

    @classmethod
    def upsert(cls, entity: EntityKind, entity_id: str) -> QueueEntry:
        return cls(entity=entity, entity_id=entity_id, op="upsert", queued_at=utc_now_iso())


class SyncQueue:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._path = (data_dir or resolve_data_dir(APP_ID)) / "sync_queue.json"

    def _load_entries(self) -> list[QueueEntry]:
        raw = read_json(self._path, {"entries": []})
        entries: list[QueueEntry] = []
        for item in raw.get("entries", []):
            try:
                entries.append(QueueEntry(**item))
            except TypeError:
                continue
        return entries

    def _save_entries(self, entries: list[QueueEntry]) -> None:
        atomic_write_json(self._path, {"entries": [asdict(e) for e in entries]})

    def enqueue(self, entity: EntityKind, entity_id: str) -> None:
        entries = self._load_entries()
        entries = [e for e in entries if not (e.entity == entity and e.entity_id == entity_id)]
        entries.append(QueueEntry.upsert(entity, entity_id))
        self._save_entries(entries)

    def drain(self) -> list[QueueEntry]:
        entries = self._load_entries()
        self._save_entries([])
        return entries

    def pending_count(self) -> int:
        return len(self._load_entries())
