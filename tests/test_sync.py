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

    def test_apply_remote_tombstone_hides_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from flowstate.store.todo_store import TodoStore

            store = TodoStore(data_dir=Path(tmp))
            item = store.add("Will delete remotely")
            assert item is not None
            item_id = item.id
            self.assertEqual(len(store.items), 1)
            applied = store.apply_remote_task(
                {
                    "id": item_id,
                    "title": "Will delete remotely",
                    "completed": False,
                    "notes": "",
                    "created_at": item.created_at,
                    "client_updated_at": "2099-01-01T00:00:00+00:00",
                    "deleted_at": "2099-01-01T00:00:00+00:00",
                }
            )
            self.assertTrue(applied)
            self.assertEqual(len(store.items), 0)
            raw = json.loads((Path(tmp) / "todos.json").read_text(encoding="utf-8"))
            self.assertIsNotNone(raw["items"][0]["deleted_at"])

    def test_stale_remote_does_not_overwrite_newer_local_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            from flowstate.store.todo_store import TodoStore

            store = TodoStore(data_dir=Path(tmp))
            item = store.add("Local delete wins")
            assert item is not None
            store.remove(item.id)
            deleted = store.get_sync_item(item.id)
            assert deleted is not None
            applied = store.apply_remote_task(
                {
                    "id": item.id,
                    "title": "Local delete wins",
                    "completed": False,
                    "notes": "",
                    "created_at": deleted.created_at,
                    "client_updated_at": "2000-01-01T00:00:00+00:00",
                    "deleted_at": None,
                }
            )
            self.assertFalse(applied)
            self.assertEqual(len(store.items), 0)
            self.assertIsNotNone(store.get_sync_item(item.id).deleted_at)


class SyncOrderTests(unittest.TestCase):
    def test_run_sync_pulls_before_push(self) -> None:
        """Guard against regressing to push-then-pull (resurrects deletes)."""
        import inspect

        from flowstate.sync import engine as engine_mod

        source = inspect.getsource(engine_mod.SyncEngine.run_sync)
        pull_at = source.find("self._pull(")
        push_at = source.find("self._push(")
        self.assertNotEqual(pull_at, -1)
        self.assertNotEqual(push_at, -1)
        self.assertLess(pull_at, push_at)


class TimeutilTests(unittest.TestCase):
    def test_delta_since_buffer(self) -> None:
        since = delta_since("2026-01-01T00:00:10+00:00", buffer_seconds=10)
        self.assertTrue(since.startswith("2026-01-01T00:00:00"))
        self.assertTrue(utc_now_iso().endswith("+00:00") or "+" in utc_now_iso())


if __name__ == "__main__":
    unittest.main()
