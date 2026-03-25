#!/usr/bin/env python3
"""CLI Todo App — A simple terminal task manager."""

import difflib
import shutil
import sys

from todo import tasks
from todo.storage import (
    CorruptedFileError,
    PermissionDeniedError,
    Storage,
    WriteError,
)

VERSION = "0.1.0"

COMMANDS = ["add", "list", "done", "delete", "edit", "help"]

HELP_TEXT = """\
Usage: todo <command> [arguments]

Commands:
  add <description>           Add a new task
  list [--done|--pending]     List tasks (optionally filtered by status)
  done <id>                   Mark a task as completed
  delete [-f] <id>            Delete a task (with confirmation)
  edit <id> <description>     Update a task's description
  help [command]              Show help (optionally for a specific command)

Options:
  --help, -h                  Show this help message
  --version                   Show version

Examples:
  todo add "Buy groceries"
  todo list --pending
  todo done 3
  todo delete 2
  todo edit 1 "Buy groceries and snacks"
"""

COMMAND_HELP = {
    "add": """\
Usage: todo add <description>

Add a new task with the given description. The task starts as pending
and gets an auto-assigned ID.

Examples:
  todo add "Buy groceries"
  todo add Fix the bug in login page
""",
    "list": """\
Usage: todo list [--done|--pending|--all]

List all tasks in a formatted table. Optionally filter by status.

Options:
  --pending    Show only pending tasks
  --done       Show only completed tasks
  --all        Show all tasks (default)

Examples:
  todo list
  todo list --pending
  todo list --done
""",
    "done": """\
Usage: todo done <id>

Mark a task as completed by its ID.

Examples:
  todo done 3
  todo done 1
""",
    "delete": """\
Usage: todo delete [-f|--force] <id>

Delete a task by its ID. Asks for confirmation unless --force is used.

Options:
  -f, --force    Skip confirmation prompt

Examples:
  todo delete 2
  todo delete --force 5
""",
    "edit": """\
Usage: todo edit <id> <description>

Update a task's description. Shows the old and new values.

Examples:
  todo edit 3 "Buy groceries and snacks"
  todo edit 1 Fix the login page bug
""",
    "help": """\
Usage: todo help [command]

Show general help or detailed help for a specific command.

Examples:
  todo help
  todo help add
  todo help list
""",
}


def parse_id(raw):
    """Parse and validate a task ID from CLI input."""
    try:
        task_id = int(raw)
    except ValueError:
        error(f"Task ID must be a positive number.")
        return None
    if task_id <= 0:
        error(f"Task ID must be a positive number.")
        return None
    return task_id


def error(message, hint=None):
    """Print an error message to stderr."""
    print(f"Error: {message}", file=sys.stderr)
    if hint:
        print(f"Usage: {hint}", file=sys.stderr)


def format_table(task_list, terminal_width=None):
    """Format tasks as a table string."""
    if terminal_width is None:
        terminal_width = shutil.get_terminal_size().columns

    # Column widths
    id_w = 4
    status_w = 8
    date_w = 12
    # Description gets the rest minus separators
    desc_w = max(terminal_width - id_w - status_w - date_w - 6, 20)

    header = (
        f"{'ID':<{id_w}}  {'Status':<{status_w}}  {'Description':<{desc_w}}  {'Created':<{date_w}}"
    )
    separator = "-" * len(header)

    lines = [header, separator]
    for t in task_list:
        status = "[x]" if t["status"] == "done" else "[ ]"
        desc = t["description"]
        if len(desc) > desc_w:
            desc = desc[: desc_w - 3] + "..."
        created = t.get("created_at", "")[:10]
        lines.append(
            f"{t['id']:<{id_w}}  {status:<{status_w}}  {desc:<{desc_w}}  {created:<{date_w}}"
        )

    return "\n".join(lines)


def format_summary(displayed_tasks, all_tasks, status_filter=None):
    """Format a summary line for the task list."""
    total = len(all_tasks)
    pending = sum(1 for t in all_tasks if t["status"] == "pending")
    done = sum(1 for t in all_tasks if t["status"] == "done")
    shown = len(displayed_tasks)

    if status_filter == "pending":
        noun = "task" if shown == 1 else "tasks"
        return f"\nShowing {shown} pending {noun} ({total} total)."
    elif status_filter == "done":
        noun = "task" if shown == 1 else "tasks"
        return f"\nShowing {shown} completed {noun} ({total} total)."
    else:
        noun = "task" if total == 1 else "tasks"
        return f"\n{total} {noun} ({pending} pending, {done} done)."


# --- Command handlers ---


def cmd_add(storage, args):
    description = " ".join(args)
    if not description.strip():
        error("Please provide a task description.", "todo add <description>")
        return 1
    try:
        task = tasks.add(storage, description)
    except ValueError as e:
        error(str(e), "todo add <description>")
        return 1
    print(f"Added task {task['id']}: {task['description']}")
    return 0


def cmd_list(storage, args):
    # Parse flags
    valid_flags = {"--done", "--pending", "--all"}
    flags = [a for a in args if a.startswith("--")]
    unknown_flags = [f for f in flags if f not in valid_flags]

    if unknown_flags:
        error(
            f'Unknown option "{unknown_flags[0]}". Available filters: --done, --pending'
        )
        return 1

    has_done = "--done" in flags
    has_pending = "--pending" in flags

    if has_done and has_pending:
        error("Cannot use --done and --pending together. Use `todo list` to see all tasks.")
        return 1

    status_filter = None
    if has_done:
        status_filter = "done"
    elif has_pending:
        status_filter = "pending"

    all_tasks = tasks.list_tasks(storage)
    displayed = tasks.list_tasks(storage, status_filter=status_filter)

    if not all_tasks:
        print('No tasks yet. Add one with: todo add "your task"')
        return 0

    if not displayed:
        label = status_filter or "matching"
        print(f"No {label} tasks. Run `todo list` to see all tasks.")
        return 0

    print(format_table(displayed))
    print(format_summary(displayed, all_tasks, status_filter))
    return 0


def cmd_done(storage, args):
    if not args:
        error("Please provide a task ID.", "todo done <id>")
        return 1

    task_id = parse_id(args[0])
    if task_id is None:
        return 1

    try:
        task, already_done = tasks.complete(storage, task_id)
    except ValueError:
        error(f"Task {task_id} not found.")
        return 1

    if already_done:
        print(f"Task {task_id} is already completed.")
    else:
        print(f"Completed task {task_id}: {task['description']}")
    return 0


def cmd_delete(storage, args):
    # Parse --force / -f flag
    force = False
    remaining = []
    for a in args:
        if a in ("--force", "-f"):
            force = True
        else:
            remaining.append(a)

    if not remaining:
        error("Please provide a task ID.", "todo delete <id>")
        return 1

    task_id = parse_id(remaining[0])
    if task_id is None:
        return 1

    # Check task exists
    task = tasks.get(storage, task_id)
    if task is None:
        error(f"Task {task_id} not found.")
        return 1

    if not force:
        status = task["status"]
        desc = task["description"]
        try:
            answer = input(f"Delete task {task_id} [{status}]: {desc}? [y/N] ")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 0
        if answer.strip().lower() != "y":
            print("Cancelled.")
            return 0

    deleted = tasks.delete(storage, task_id)
    print(f"Deleted task {task_id}: {deleted['description']}")
    return 0


def cmd_edit(storage, args):
    if not args:
        error(
            "Please provide a task ID and new description.",
            "todo edit <id> <description>",
        )
        return 1

    task_id = parse_id(args[0])
    if task_id is None:
        return 1

    if len(args) < 2:
        error("Please provide a new description.", "todo edit <id> <description>")
        return 1

    new_description = " ".join(args[1:])

    # Check if task is completed and warn
    task = tasks.get(storage, task_id)
    if task is None:
        error(f"Task {task_id} not found.")
        return 1

    if task["status"] == "done":
        print(f"Warning: Task {task_id} is already completed.", file=sys.stderr)

    try:
        updated, old_desc, changed = tasks.edit(storage, task_id, new_description)
    except ValueError as e:
        error(str(e))
        return 1

    if not changed:
        print(f"No changes made — description is already: {updated['description']}")
    else:
        print(f'Updated task {task_id}: "{old_desc}" -> "{updated["description"]}"')
    return 0


def cmd_help(storage, args):
    if args:
        cmd_name = args[0]
        if cmd_name in COMMAND_HELP:
            print(COMMAND_HELP[cmd_name], end="")
        else:
            error(
                f'Unknown command: {cmd_name}. Run `todo help` for available commands.'
            )
            return 1
    else:
        print(HELP_TEXT, end="")
    return 0


DISPATCH = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "delete": cmd_delete,
    "edit": cmd_edit,
    "help": cmd_help,
}


def suggest_command(unknown):
    """Suggest a similar command using difflib."""
    matches = difflib.get_close_matches(unknown, COMMANDS, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    return None


def main():
    args = sys.argv[1:]

    # Handle global flags
    if not args or args[0] in ("--help", "-h"):
        print(HELP_TEXT, end="")
        return 0

    if args[0] == "--version":
        print(f"todo v{VERSION}")
        return 0

    command = args[0]
    command_args = args[1:]

    # Initialize storage
    storage = Storage()
    try:
        storage.initialize()
    except PermissionDeniedError as e:
        error(str(e))
        return 1

    # Route command
    if command in DISPATCH:
        try:
            return DISPATCH[command](storage, command_args)
        except CorruptedFileError as e:
            error(str(e))
            return 1
        except PermissionDeniedError as e:
            error(str(e))
            return 1
        except WriteError as e:
            error(str(e))
            return 1
    else:
        suggestion = suggest_command(command)
        if suggestion:
            error(f'Unknown command: {command}. Did you mean: {suggestion}?')
        else:
            error(f'Unknown command: {command}. Run `todo help` for usage.')
        print(HELP_TEXT, end="")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)
