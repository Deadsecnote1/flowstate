# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for persistence (no display required)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_write_roundtrip(self) -> None:
        from flowstate.store.base import atomic_write_json, read_json

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "data.json"
            atomic_write_json(path, {"items": [1, 2]})
            self.assertEqual(read_json(path, {}), {"items": [1, 2]})

    def test_corrupt_json_returns_default_and_status(self) -> None:
        from flowstate.store.base import read_json_with_status

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            data, ok = read_json_with_status(path, {"items": []})
            self.assertFalse(ok)
            self.assertEqual(data, {"items": []})


class TodoStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.data_dir = Path(self._tmpdir.name)
        from flowstate.store.todo_store import TodoStore

        self.TodoStore = TodoStore

    def test_add_toggle_archive(self) -> None:
        store = self.TodoStore(data_dir=self.data_dir)
        item = store.add("Ship release")
        assert item is not None
        self.assertEqual(len(store.items), 1)
        store.toggle(item.id)
        archived = store.archive_completed()
        self.assertEqual(archived, 1)
        self.assertEqual(len(store.items), 0)

        archive_path = self.data_dir / "todos_archive.json"
        payload = json.loads(archive_path.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["title"], "Ship release")

    def test_valid_json_with_invalid_shape_sets_load_error(self) -> None:
        path = self.data_dir / "todos.json"
        path.write_text("[]", encoding="utf-8")
        store = self.TodoStore(data_dir=self.data_dir)
        self.assertIsNotNone(store.load_error)
        self.assertEqual(store.items, [])

    def test_corrupt_file_sets_load_error(self) -> None:
        path = self.data_dir / "todos.json"
        path.write_text("{{{", encoding="utf-8")
        store = self.TodoStore(data_dir=self.data_dir)
        self.assertIsNotNone(store.load_error)
        self.assertEqual(store.items, [])
        self.assertTrue((self.data_dir / "todos.json.bak").exists())


if __name__ == "__main__":
    unittest.main()
