# CLI Todo App — Product Requirements Document

## Overview

A command-line todo application that lets users manage tasks from the terminal. Tasks are stored locally in a JSON file so they persist between sessions.

## Goals

- Learn fundamental programming concepts (data structures, file I/O, control flow)
- Build a usable tool that runs entirely in the terminal
- Practice incremental development with git

## Target User

A developer (or aspiring developer) who lives in the terminal and wants a lightweight task manager without leaving the command line.

## Core Features

### 1. Add a Task
- User provides a task description
- Task is assigned a unique numeric ID automatically
- Task starts with status "pending"
- Example: `todo add "Buy groceries"`

### 2. List Tasks
- Display all tasks in a formatted table
- Show ID, status, description, and created date
- Support filtering: `todo list`, `todo list --done`, `todo list --pending`

### 3. Complete a Task
- Mark a task as done by its ID
- Example: `todo done 3`

### 4. Delete a Task
- Remove a task by its ID
- Example: `todo delete 3`

### 5. Edit a Task
- Update the description of an existing task
- Example: `todo edit 3 "Buy groceries and snacks"`

## Data Model

Each task contains:
| Field       | Type     | Description                     |
|-------------|----------|---------------------------------|
| id          | integer  | Auto-incrementing unique ID     |
| description | string   | The task text                   |
| status      | string   | "pending" or "done"             |
| created_at  | string   | ISO 8601 timestamp              |
| completed_at| string   | ISO 8601 timestamp (when done)  |

## Storage

- Tasks are stored in `~/.todo/tasks.json`
- The file is created automatically on first use
- Format: JSON array of task objects

## CLI Interface

```
Usage: todo <command> [arguments]

Commands:
  add <description>        Add a new task
  list [--done|--pending]  List tasks (optionally filtered)
  done <id>                Mark a task as completed
  delete <id>              Delete a task
  edit <id> <description>  Update a task's description
  help                     Show this help message
```

## Non-Functional Requirements

- **Language:** Python (beginner-friendly, no compilation needed)
- **Dependencies:** None — standard library only
- **Compatibility:** macOS, Linux, Windows
- **Performance:** Instant for typical usage (< 1000 tasks)

## Future Enhancements (Out of Scope for v1)

- Priority levels (low / medium / high)
- Due dates with overdue highlighting
- Tags / categories
- Search by keyword
- Export to CSV or markdown

## Milestones

1. **M1:** Project setup + `add` and `list` commands
2. **M2:** `done` and `delete` commands
3. **M3:** `edit` command + filtered listing
4. **M4:** Polish — error handling, help text, edge cases
