# SPDX-License-Identifier: GPL-3.0-or-later
"""Regression tests for planner occurrences and inbox scheduling."""

import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from flowstate.store.planner_store import PlannerStore, PlanTask


class PlannerStoreTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data_dir = Path(tmp.name)
        (self.data_dir / "planner.json").write_text('{"tasks": [], "inbox": []}')
        self.store = PlannerStore(data_dir=self.data_dir)
        self.start = date(2024, 1, 1)
        self.tomorrow = self.start + timedelta(days=1)
        self.series = self.store.add(replace(PlanTask.create("Original", self.start), repeat="daily"))

    def test_occurrence_edit_and_delete_survive_reload(self):
        occurrence, = self.store.tasks_for_day(self.tomorrow)
        edited = replace(occurrence, title="Edited", start_min=570)
        self.store.update(edited)
        self.store.update(edited)
        reloaded = PlannerStore(data_dir=self.data_dir)
        saved, = reloaded.tasks_for_day(self.tomorrow)
        self.assertEqual((saved.title, saved.start_min), ("Edited", 570))
        reloaded.remove(saved.id)
        reloaded = PlannerStore(data_dir=self.data_dir)
        self.assertEqual(reloaded.tasks_for_day(self.tomorrow), [])
        following, = reloaded.tasks_for_day(self.tomorrow + timedelta(days=1))
        self.assertEqual(following.title, "Original")
        self.assertEqual(reloaded.tasks_for_day(self.start), [self.series])

    def test_complete_one_of_two_identical_series(self):
        self.store.add(replace(PlanTask.create("Original", self.start), repeat="daily"))
        first, second = self.store.tasks_for_day(self.tomorrow)
        self.store.toggle_complete(first.id)
        rows = PlannerStore(data_dir=self.data_dir).tasks_for_day(self.tomorrow)
        self.assertEqual(len(rows), 2)
        self.assertIn(second.id, [row.id for row in rows if not row.completed])

    def test_schedule_inbox_item(self):
        self.store.add_inbox("Schedule me")
        item, = self.store.inbox
        task = PlanTask.create(item["title"], self.tomorrow)
        self.store.add(task, inbox_id=item["id"])
        reloaded = PlannerStore(data_dir=self.data_dir)
        self.assertEqual(reloaded.inbox, [])
        self.assertEqual(reloaded.get(task.id), task)
