import json
import os
import subprocess
import sys
import tempfile
import unittest


def run_todo(args, tmp_dir, stdin_text=None):
    """Run todo.py as a subprocess with HOME set to tmp_dir."""
    env = os.environ.copy()
    env["HOME"] = tmp_dir
    result = subprocess.run(
        [sys.executable, "todo.py"] + args,
        capture_output=True,
        text=True,
        env=env,
        input=stdin_text,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return result


class CLITestCase(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.todo_dir = os.path.join(self.tmp_dir, ".todo")
        self.tasks_file = os.path.join(self.todo_dir, "tasks.json")

    def _init_storage(self, task_list=None):
        os.makedirs(self.todo_dir, exist_ok=True)
        with open(self.tasks_file, "w") as f:
            json.dump(task_list or [], f)

    def _load_tasks(self):
        with open(self.tasks_file) as f:
            return json.load(f)


class TestCLIHelp(CLITestCase):
    def test_no_args_shows_help(self):
        r = run_todo([], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Usage: todo", r.stdout)

    def test_help_command(self):
        r = run_todo(["help"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("add", r.stdout)
        self.assertIn("list", r.stdout)
        self.assertIn("done", r.stdout)
        self.assertIn("delete", r.stdout)
        self.assertIn("edit", r.stdout)
        self.assertIn("--done", r.stdout)
        self.assertIn("--pending", r.stdout)

    def test_help_flag(self):
        r = run_todo(["--help"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Usage: todo", r.stdout)

    def test_h_flag(self):
        r = run_todo(["-h"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Usage: todo", r.stdout)

    def test_version(self):
        r = run_todo(["--version"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("todo v", r.stdout)

    def test_per_command_help(self):
        r = run_todo(["help", "add"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("todo add", r.stdout)

    def test_help_unknown_command(self):
        r = run_todo(["help", "foobar"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Unknown command", r.stderr)


class TestCLIUnknownCommand(CLITestCase):
    def test_unknown_command(self):
        self._init_storage()
        r = run_todo(["foobar"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Unknown command: foobar", r.stderr)

    def test_similar_command_suggestion(self):
        self._init_storage()
        r = run_todo(["lst"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Did you mean: list?", r.stderr)


class TestCLIAdd(CLITestCase):
    def test_add_task(self):
        self._init_storage()
        r = run_todo(["add", "Buy groceries"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Added task 1: Buy groceries", r.stdout)
        tasks = self._load_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["description"], "Buy groceries")

    def test_add_no_description(self):
        self._init_storage()
        r = run_todo(["add"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Error", r.stderr)
        self.assertIn("description", r.stderr)

    def test_add_whitespace_only(self):
        self._init_storage()
        r = run_todo(["add", "   "], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Error", r.stderr)


class TestCLIList(CLITestCase):
    def test_list_empty(self):
        self._init_storage()
        r = run_todo(["list"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("No tasks yet", r.stdout)
        self.assertIn("todo add", r.stdout)

    def test_list_with_tasks(self):
        self._init_storage([
            {"id": 1, "description": "Task A", "status": "pending",
             "created_at": "2026-03-25T10:00:00", "completed_at": None},
            {"id": 2, "description": "Task B", "status": "done",
             "created_at": "2026-03-25T11:00:00", "completed_at": "2026-03-25T12:00:00"},
        ])
        r = run_todo(["list"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("[ ]", r.stdout)
        self.assertIn("[x]", r.stdout)
        self.assertIn("Task A", r.stdout)
        self.assertIn("Task B", r.stdout)
        self.assertIn("ID", r.stdout)  # header

    def test_list_filter_pending(self):
        self._init_storage([
            {"id": 1, "description": "Pending", "status": "pending",
             "created_at": "", "completed_at": None},
            {"id": 2, "description": "Done", "status": "done",
             "created_at": "", "completed_at": ""},
        ])
        r = run_todo(["list", "--pending"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Pending", r.stdout)
        self.assertNotIn("Done", r.stdout)
        self.assertIn("pending", r.stdout.lower())

    def test_list_filter_done(self):
        self._init_storage([
            {"id": 1, "description": "Pending", "status": "pending",
             "created_at": "", "completed_at": None},
            {"id": 2, "description": "Done", "status": "done",
             "created_at": "", "completed_at": ""},
        ])
        r = run_todo(["list", "--done"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Done", r.stdout)

    def test_list_conflicting_flags(self):
        self._init_storage()
        r = run_todo(["list", "--done", "--pending"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Cannot use --done and --pending together", r.stderr)

    def test_list_unknown_flag(self):
        self._init_storage()
        r = run_todo(["list", "--completed"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Unknown option", r.stderr)

    def test_list_all_flag(self):
        self._init_storage([
            {"id": 1, "description": "A", "status": "pending",
             "created_at": "", "completed_at": None},
            {"id": 2, "description": "B", "status": "done",
             "created_at": "", "completed_at": ""},
        ])
        r = run_todo(["list", "--all"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("A", r.stdout)
        self.assertIn("B", r.stdout)

    def test_list_empty_filter(self):
        self._init_storage([
            {"id": 1, "description": "Pending", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["list", "--done"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("No done tasks", r.stdout)
        self.assertIn("todo list", r.stdout)

    def test_list_summary_with_filter(self):
        self._init_storage([
            {"id": 1, "description": "A", "status": "pending", "created_at": "", "completed_at": None},
            {"id": 2, "description": "B", "status": "pending", "created_at": "", "completed_at": None},
            {"id": 3, "description": "C", "status": "done", "created_at": "", "completed_at": ""},
        ])
        r = run_todo(["list", "--pending"], self.tmp_dir)
        self.assertIn("Showing 2 pending tasks (3 total)", r.stdout)

    def test_list_summary_singular(self):
        self._init_storage([
            {"id": 1, "description": "A", "status": "pending", "created_at": "", "completed_at": None},
        ])
        r = run_todo(["list"], self.tmp_dir)
        self.assertIn("1 task (1 pending, 0 done)", r.stdout)


class TestCLIDone(CLITestCase):
    def test_done_task(self):
        self._init_storage([
            {"id": 1, "description": "Test", "status": "pending",
             "created_at": "2026-01-01", "completed_at": None},
        ])
        r = run_todo(["done", "1"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Completed task 1", r.stdout)
        t = self._load_tasks()[0]
        self.assertEqual(t["status"], "done")

    def test_done_already_completed(self):
        self._init_storage([
            {"id": 1, "description": "Test", "status": "done",
             "created_at": "", "completed_at": "2026-01-01"},
        ])
        r = run_todo(["done", "1"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("already completed", r.stdout)

    def test_done_not_found(self):
        self._init_storage()
        r = run_todo(["done", "99"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stderr)

    def test_done_no_id(self):
        self._init_storage()
        r = run_todo(["done"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("task ID", r.stderr)
        self.assertIn("Usage:", r.stderr)

    def test_done_non_numeric_id(self):
        self._init_storage()
        r = run_todo(["done", "abc"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("positive number", r.stderr)

    def test_done_zero_id(self):
        self._init_storage()
        r = run_todo(["done", "0"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("positive number", r.stderr)

    def test_done_negative_id(self):
        self._init_storage()
        r = run_todo(["done", "-5"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("positive number", r.stderr)

    def test_done_large_id(self):
        self._init_storage()
        r = run_todo(["done", "999999999"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stderr)


class TestCLIDelete(CLITestCase):
    def test_delete_with_force(self):
        self._init_storage([
            {"id": 1, "description": "Buy groceries", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["delete", "--force", "1"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Deleted task 1: Buy groceries", r.stdout)
        self.assertEqual(self._load_tasks(), [])

    def test_delete_with_f_flag(self):
        self._init_storage([
            {"id": 1, "description": "Test", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["delete", "-f", "1"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Deleted task 1", r.stdout)

    def test_delete_with_confirmation_yes(self):
        self._init_storage([
            {"id": 1, "description": "Test", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["delete", "1"], self.tmp_dir, stdin_text="y\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Deleted task 1", r.stdout)
        self.assertEqual(self._load_tasks(), [])

    def test_delete_with_confirmation_no(self):
        self._init_storage([
            {"id": 1, "description": "Test", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["delete", "1"], self.tmp_dir, stdin_text="n\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("Cancelled", r.stdout)
        self.assertEqual(len(self._load_tasks()), 1)

    def test_delete_confirmation_shows_status(self):
        self._init_storage([
            {"id": 1, "description": "Test", "status": "done",
             "created_at": "", "completed_at": ""},
        ])
        r = run_todo(["delete", "1"], self.tmp_dir, stdin_text="n\n")
        self.assertIn("[done]", r.stdout)

    def test_delete_not_found(self):
        self._init_storage()
        r = run_todo(["delete", "--force", "99"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stderr)

    def test_delete_no_id(self):
        self._init_storage()
        r = run_todo(["delete"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("task ID", r.stderr)

    def test_delete_non_numeric_id(self):
        self._init_storage()
        r = run_todo(["delete", "abc"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("positive number", r.stderr)

    def test_delete_last_then_list(self):
        self._init_storage([
            {"id": 1, "description": "Only task", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        run_todo(["delete", "--force", "1"], self.tmp_dir)
        r = run_todo(["list"], self.tmp_dir)
        self.assertIn("No tasks yet", r.stdout)


class TestCLIEdit(CLITestCase):
    def test_edit_task(self):
        self._init_storage([
            {"id": 1, "description": "Buy groceries", "status": "pending",
             "created_at": "2026-03-25T10:00:00", "completed_at": None},
        ])
        r = run_todo(["edit", "1", "Buy groceries and snacks"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn('"Buy groceries"', r.stdout)
        self.assertIn('"Buy groceries and snacks"', r.stdout)
        self.assertIn("->", r.stdout)

    def test_edit_no_args(self):
        self._init_storage()
        r = run_todo(["edit"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("task ID", r.stderr)
        self.assertIn("Usage:", r.stderr)

    def test_edit_no_description(self):
        self._init_storage([
            {"id": 1, "description": "Old", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["edit", "1"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("description", r.stderr)

    def test_edit_empty_description(self):
        self._init_storage([
            {"id": 1, "description": "Old", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["edit", "1", "   "], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("empty", r.stderr)

    def test_edit_same_description(self):
        self._init_storage([
            {"id": 1, "description": "Same", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["edit", "1", "Same"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("No changes made", r.stdout)

    def test_edit_completed_task_warns(self):
        self._init_storage([
            {"id": 1, "description": "Old", "status": "done",
             "created_at": "", "completed_at": ""},
        ])
        r = run_todo(["edit", "1", "New"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Warning", r.stderr)
        self.assertIn("already completed", r.stderr)
        self.assertIn("Updated task 1", r.stdout)

    def test_edit_not_found(self):
        self._init_storage()
        r = run_todo(["edit", "99", "New"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not found", r.stderr)

    def test_edit_non_numeric_id(self):
        self._init_storage()
        r = run_todo(["edit", "abc", "New"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("positive number", r.stderr)

    def test_edit_multi_word_no_quotes(self):
        self._init_storage([
            {"id": 1, "description": "Old", "status": "pending",
             "created_at": "", "completed_at": None},
        ])
        r = run_todo(["edit", "1", "Buy", "groceries", "and", "snacks"], self.tmp_dir)
        self.assertEqual(r.returncode, 0)
        t = self._load_tasks()[0]
        self.assertEqual(t["description"], "Buy groceries and snacks")


class TestCLIErrorHandling(CLITestCase):
    def test_corrupted_json(self):
        os.makedirs(self.todo_dir)
        with open(self.tasks_file, "w") as f:
            f.write("{broken")
        r = run_todo(["list"], self.tmp_dir)
        self.assertEqual(r.returncode, 1)
        self.assertIn("corrupted", r.stderr)


if __name__ == "__main__":
    unittest.main()
