import json
import os
import sys
import tempfile


DEFAULT_DIR_NAME = ".todo"
DEFAULT_FILE_NAME = "tasks.json"


class StorageError(Exception):
    pass


class CorruptedFileError(StorageError):
    pass


class PermissionDeniedError(StorageError):
    pass


class WriteError(StorageError):
    pass


class Storage:
    def __init__(self, base_dir=None):
        if base_dir is None:
            base_dir = os.path.expanduser("~")
        self.dir_path = os.path.join(base_dir, DEFAULT_DIR_NAME)
        self.file_path = os.path.join(self.dir_path, DEFAULT_FILE_NAME)

    def initialize(self):
        """Create storage directory and file if they don't exist.
        Returns True if this was a first-run initialization (directory created).
        """
        first_run = not os.path.exists(self.dir_path)
        try:
            os.makedirs(self.dir_path, exist_ok=True)
        except PermissionError:
            raise PermissionDeniedError(
                f"Cannot access {self.dir_path}. Check directory permissions."
            )

        if not os.path.exists(self.file_path):
            self._atomic_write([])

        if first_run:
            print(
                f"Initialized task storage at {self.file_path}",
                file=sys.stderr,
            )

        return first_run

    def load(self):
        """Load tasks from the JSON file. Returns a list of task dicts."""
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            raise CorruptedFileError(
                f"Task file is corrupted. Please check {self.file_path}"
            )
        except PermissionError:
            raise PermissionDeniedError(
                f"Cannot access {self.file_path} — check file permissions."
            )
        return data

    def save(self, tasks):
        """Save tasks to the JSON file using atomic write."""
        self._atomic_write(tasks)

    def _atomic_write(self, data):
        """Write data to a temp file, then atomically rename to tasks.json."""
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=self.dir_path, suffix=".tmp", prefix="tasks_"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(data, f, indent=2)
                    f.write("\n")
                os.replace(tmp_path, self.file_path)
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except PermissionError:
            raise PermissionDeniedError(
                f"Cannot access {self.file_path} — check file permissions."
            )
        except OSError as e:
            raise WriteError(
                f"Could not save tasks. Check disk space and permissions. ({e})"
            )
