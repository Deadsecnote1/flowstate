# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for sync queue, merge, and tombstone stores."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flowstate.sync.merge import remote_is_newer
from flowstate.sync.queue import SyncQueue
from flowstate.sync.timeutil import delta_since, utc_now_iso


class MergeTests(unittest.TestCase):
    def test_remote_is_newer(self) -> None:
        self.assertTrue(
            remote_is_newer(
                "2026-01-01T00:00:00+00:00",
                {"client_updated_at": "2026-01-02T00:00:00+00:00"},
            )
        )
        self.assertFalse(
            remote_is_newer(
                "2026-01-03T00:00:00+00:00",
                {"client_updated_at": "2026-01-02T00:00:00+00:00"},
            )
        )


class QueueTests(unittest.TestCase):
    def test_queue_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            q = SyncQueue(data)
            q.enqueue("task", "abc")
            self.assertEqual(q.pending_count(), 1)
            q2 = SyncQueue(data)
            self.assertEqual(q2.pending_count(), 1)
            drained = q2.drain()
            self.assertEqual(len(drained), 1)
            self.assertEqual(drained[0].entity_id, "abc")


class TombstoneTests(unittest.TestCase):
    def test_remove_sets_deleted_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from flowstate.store.todo_store import TodoStore

            store = TodoStore(data_dir=Path(tmp))
            item = store.add("Sync me")
            assert item is not None
            store.remove(item.id)
            self.assertEqual(len(store.items), 0)
            raw = json.loads((Path(tmp) / "todos.json").read_text(encoding="utf-8"))
            self.assertIsNotNone(raw["items"][0]["deleted_at"])

    def test_apply_remote_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from flowstate.store.todo_store import TodoStore

            store = TodoStore(data_dir=Path(tmp))
            applied = store.apply_remote_task(
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "From cloud",
                    "completed": False,
                    "notes": "",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "client_updated_at": "2026-01-01T00:00:00+00:00",
                    "deleted_at": None,
                }
            )
            self.assertTrue(applied)
            self.assertEqual(len(store.items), 1)
            self.assertEqual(store.items[0].title, "From cloud")


class TimeutilTests(unittest.TestCase):
    def test_delta_since_buffer(self) -> None:
        since = delta_since("2026-01-01T00:00:10+00:00", buffer_seconds=10)
        self.assertTrue(since.startswith("2026-01-01T00:00:00"))
        self.assertTrue(utc_now_iso().endswith("+00:00") or "+" in utc_now_iso())


if __name__ == "__main__":
    unittest.main()
