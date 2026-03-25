import json
import os
import stat
import tempfile
import unittest

from todo.storage import (
    CorruptedFileError,
    PermissionDeniedError,
    Storage,
)


class TestStorageInitialize(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage = Storage(base_dir=self.tmp_dir)

    def test_creates_directory_and_file_when_missing(self):
        result = self.storage.initialize()
        self.assertTrue(result)  # first run
        self.assertTrue(os.path.isdir(self.storage.dir_path))
        self.assertTrue(os.path.isfile(self.storage.file_path))
        with open(self.storage.file_path) as f:
            self.assertEqual(json.load(f), [])

    def test_creates_file_when_directory_exists(self):
        os.makedirs(self.storage.dir_path)
        result = self.storage.initialize()
        self.assertFalse(result)  # dir existed
        self.assertTrue(os.path.isfile(self.storage.file_path))
        with open(self.storage.file_path) as f:
            self.assertEqual(json.load(f), [])

    def test_does_not_overwrite_existing_file(self):
        os.makedirs(self.storage.dir_path)
        existing = [{"id": 1, "description": "existing"}]
        with open(self.storage.file_path, "w") as f:
            json.dump(existing, f)

        self.storage.initialize()
        with open(self.storage.file_path) as f:
            self.assertEqual(json.load(f), existing)


class TestStorageLoad(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage = Storage(base_dir=self.tmp_dir)
        self.storage.initialize()

    def test_load_empty(self):
        tasks = self.storage.load()
        self.assertEqual(tasks, [])

    def test_load_with_tasks(self):
        data = [{"id": 1, "description": "test"}]
        with open(self.storage.file_path, "w") as f:
            json.dump(data, f)
        tasks = self.storage.load()
        self.assertEqual(tasks, data)

    def test_load_corrupted_file(self):
        with open(self.storage.file_path, "w") as f:
            f.write("{broken json")
        with self.assertRaises(CorruptedFileError):
            self.storage.load()


class TestStorageSave(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.storage = Storage(base_dir=self.tmp_dir)
        self.storage.initialize()

    def test_save_and_load_roundtrip(self):
        tasks = [{"id": 1, "description": "test", "status": "pending"}]
        self.storage.save(tasks)
        loaded = self.storage.load()
        self.assertEqual(loaded, tasks)

    def test_atomic_write_preserves_original_on_permission_error(self):
        tasks = [{"id": 1, "description": "original"}]
        self.storage.save(tasks)

        # Make the directory read-only to prevent temp file creation
        os.chmod(self.storage.dir_path, stat.S_IRUSR | stat.S_IXUSR)
        try:
            with self.assertRaises(PermissionDeniedError):
                self.storage.save([{"id": 2, "description": "new"}])
        finally:
            # Restore permissions for cleanup
            os.chmod(
                self.storage.dir_path,
                stat.S_IRWXU,
            )

        loaded = self.storage.load()
        self.assertEqual(loaded, tasks)


class TestStoragePermissions(unittest.TestCase):
    def test_permission_error_on_read_only_dir(self):
        tmp_dir = tempfile.mkdtemp()
        storage = Storage(base_dir=tmp_dir)
        storage.initialize()

        # Make file unreadable
        os.chmod(storage.file_path, 0o000)
        try:
            with self.assertRaises(PermissionDeniedError):
                storage.load()
        finally:
            os.chmod(storage.file_path, stat.S_IRWXU)


if __name__ == "__main__":
    unittest.main()
