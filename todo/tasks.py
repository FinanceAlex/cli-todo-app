import datetime


def _next_id(tasks):
    if not tasks:
        return 1
    return max(t["id"] for t in tasks) + 1


def add(storage, description):
    """Add a new task. Returns the created task dict."""
    description = description.replace("\n", " ").replace("\r", " ").strip()
    if not description:
        raise ValueError("Task description cannot be empty.")

    tasks = storage.load()
    task = {
        "id": _next_id(tasks),
        "description": description,
        "status": "pending",
        "created_at": datetime.datetime.now().isoformat(),
        "completed_at": None,
    }
    tasks.append(task)
    storage.save(tasks)
    return task


def list_tasks(storage, status_filter=None):
    """List tasks, optionally filtered by status. Returns sorted list."""
    tasks = storage.load()
    if status_filter:
        tasks = [t for t in tasks if t["status"] == status_filter]
    return sorted(tasks, key=lambda t: t["id"])


def complete(storage, task_id):
    """Mark a task as done. Returns (task, already_done) tuple."""
    tasks = storage.load()
    for task in tasks:
        if task["id"] == task_id:
            if task["status"] == "done":
                return task, True
            task["status"] = "done"
            task["completed_at"] = datetime.datetime.now().isoformat()
            storage.save(tasks)
            return task, False
    raise ValueError(f"Task {task_id} not found.")


def delete(storage, task_id):
    """Delete a task by ID. Returns the deleted task."""
    tasks = storage.load()
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            storage.save(tasks)
            return task
    raise ValueError(f"Task {task_id} not found.")


def get(storage, task_id):
    """Get a single task by ID. Returns task dict or None."""
    tasks = storage.load()
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def edit(storage, task_id, new_description):
    """Edit a task's description. Returns (task, old_description)."""
    new_description = new_description.replace("\n", " ").replace("\r", " ").strip()
    if not new_description:
        raise ValueError("Description cannot be empty.")

    tasks = storage.load()
    for task in tasks:
        if task["id"] == task_id:
            old_description = task["description"]
            if old_description == new_description:
                return task, old_description, False  # no change
            task["description"] = new_description
            task["updated_at"] = datetime.datetime.now().isoformat()
            storage.save(tasks)
            return task, old_description, True  # changed
    raise ValueError(f"Task {task_id} not found.")
