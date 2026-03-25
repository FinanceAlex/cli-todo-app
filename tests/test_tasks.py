import json
import os
import tempfile
import unittest

from todo.storage import Storage
from todo import tasks


class TaskTestCase(unittest.TestCase):
    """Base class providing a temporary storage for task tests."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage = Storage(base_dir=self.tmp_dir)
        self.storage.initialize()

    def _save_tasks(self, task_list):
        self.storage.save(task_list)

    def _load_tasks(self):
        return self.storage.load()


class TestAddTask(TaskTestCase):
    def test_add_first_task(self):
        task = tasks.add(self.storage, "Buy groceries")
        self.assertEqual(task["id"], 1)
        self.assertEqual(task["description"], "Buy groceries")
        self.assertEqual(task["status"], "pending")
        self.assertIsNotNone(task["created_at"])
        self.assertIsNone(task["completed_at"])
        self.assertEqual(len(self._load_tasks()), 1)

    def test_add_increments_id(self):
        self._save_tasks([{"id": 5, "description": "old", "status": "pending",
                           "created_at": "2026-01-01", "completed_at": None}])
        task = tasks.add(self.storage, "New task")
        self.assertEqual(task["id"], 6)
        self.assertEqual(len(self._load_tasks()), 2)

    def test_add_empty_description_rejected(self):
        with self.assertRaises(ValueError):
            tasks.add(self.storage, "")
        self.assertEqual(len(self._load_tasks()), 0)

    def test_add_whitespace_only_rejected(self):
        with self.assertRaises(ValueError):
            tasks.add(self.storage, "   ")
        self.assertEqual(len(self._load_tasks()), 0)

    def test_add_strips_whitespace(self):
        task = tasks.add(self.storage, "  Buy groceries  ")
        self.assertEqual(task["description"], "Buy groceries")

    def test_add_flattens_newlines(self):
        task = tasks.add(self.storage, "Line one\nLine two")
        self.assertEqual(task["description"], "Line one Line two")

    def test_add_special_characters(self):
        task = tasks.add(self.storage, 'Buy "fancy" groceries & snacks')
        self.assertEqual(task["description"], 'Buy "fancy" groceries & snacks')
        # Verify JSON roundtrip
        loaded = self._load_tasks()
        self.assertEqual(loaded[0]["description"], 'Buy "fancy" groceries & snacks')


class TestListTasks(TaskTestCase):
    def test_list_empty(self):
        result = tasks.list_tasks(self.storage)
        self.assertEqual(result, [])

    def test_list_sorted_by_id(self):
        self._save_tasks([
            {"id": 3, "description": "c", "status": "pending", "created_at": "", "completed_at": None},
            {"id": 1, "description": "a", "status": "done", "created_at": "", "completed_at": ""},
            {"id": 2, "description": "b", "status": "pending", "created_at": "", "completed_at": None},
        ])
        result = tasks.list_tasks(self.storage)
        self.assertEqual([t["id"] for t in result], [1, 2, 3])

    def test_list_filter_pending(self):
        self._save_tasks([
            {"id": 1, "description": "a", "status": "pending", "created_at": "", "completed_at": None},
            {"id": 2, "description": "b", "status": "done", "created_at": "", "completed_at": ""},
            {"id": 3, "description": "c", "status": "pending", "created_at": "", "completed_at": None},
        ])
        result = tasks.list_tasks(self.storage, status_filter="pending")
        self.assertEqual(len(result), 2)
        self.assertTrue(all(t["status"] == "pending" for t in result))

    def test_list_filter_done(self):
        self._save_tasks([
            {"id": 1, "description": "a", "status": "pending", "created_at": "", "completed_at": None},
            {"id": 2, "description": "b", "status": "done", "created_at": "", "completed_at": ""},
        ])
        result = tasks.list_tasks(self.storage, status_filter="done")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "done")


class TestCompleteTask(TaskTestCase):
    def test_complete_pending_task(self):
        self._save_tasks([{"id": 1, "description": "test", "status": "pending",
                           "created_at": "2026-01-01", "completed_at": None}])
        task, already_done = tasks.complete(self.storage, 1)
        self.assertEqual(task["status"], "done")
        self.assertIsNotNone(task["completed_at"])
        self.assertFalse(already_done)

    def test_complete_already_done(self):
        self._save_tasks([{"id": 1, "description": "test", "status": "done",
                           "created_at": "2026-01-01", "completed_at": "2026-01-02"}])
        task, already_done = tasks.complete(self.storage, 1)
        self.assertTrue(already_done)
        self.assertEqual(task["completed_at"], "2026-01-02")  # not changed

    def test_complete_nonexistent(self):
        with self.assertRaises(ValueError):
            tasks.complete(self.storage, 99)


class TestDeleteTask(TaskTestCase):
    def test_delete_existing(self):
        self._save_tasks([
            {"id": 1, "description": "a", "status": "pending", "created_at": "", "completed_at": None},
            {"id": 2, "description": "b", "status": "pending", "created_at": "", "completed_at": None},
        ])
        deleted = tasks.delete(self.storage, 1)
        self.assertEqual(deleted["id"], 1)
        remaining = self._load_tasks()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["id"], 2)

    def test_delete_nonexistent(self):
        with self.assertRaises(ValueError):
            tasks.delete(self.storage, 99)

    def test_delete_preserves_ids(self):
        self._save_tasks([
            {"id": 1, "description": "a", "status": "pending", "created_at": "", "completed_at": None},
            {"id": 2, "description": "b", "status": "pending", "created_at": "", "completed_at": None},
            {"id": 3, "description": "c", "status": "pending", "created_at": "", "completed_at": None},
        ])
        tasks.delete(self.storage, 2)
        new_task = tasks.add(self.storage, "New")
        self.assertEqual(new_task["id"], 4)  # max(1,3) + 1, not 3


class TestEditTask(TaskTestCase):
    def test_edit_updates_description(self):
        self._save_tasks([{"id": 1, "description": "Old text", "status": "pending",
                           "created_at": "2026-03-25T10:00:00", "completed_at": None}])
        task, old_desc, changed = tasks.edit(self.storage, 1, "New text")
        self.assertTrue(changed)
        self.assertEqual(task["description"], "New text")
        self.assertEqual(old_desc, "Old text")
        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["created_at"], "2026-03-25T10:00:00")
        self.assertIn("updated_at", task)

    def test_edit_nonexistent(self):
        with self.assertRaises(ValueError):
            tasks.edit(self.storage, 99, "New text")

    def test_edit_empty_description_rejected(self):
        self._save_tasks([{"id": 1, "description": "Old", "status": "pending",
                           "created_at": "", "completed_at": None}])
        with self.assertRaises(ValueError):
            tasks.edit(self.storage, 1, "")

    def test_edit_whitespace_description_rejected(self):
        self._save_tasks([{"id": 1, "description": "Old", "status": "pending",
                           "created_at": "", "completed_at": None}])
        with self.assertRaises(ValueError):
            tasks.edit(self.storage, 1, "   ")

    def test_edit_same_description_no_change(self):
        self._save_tasks([{"id": 1, "description": "Same", "status": "pending",
                           "created_at": "", "completed_at": None}])
        task, old_desc, changed = tasks.edit(self.storage, 1, "Same")
        self.assertFalse(changed)
        self.assertEqual(old_desc, "Same")


if __name__ == "__main__":
    unittest.main()
