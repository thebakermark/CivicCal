import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.backup_sqlite import create_backup, verify_database
from scripts.sqlite_storage import import_json_documents
from tests.test_sqlite_storage import fixture_documents


class SQLiteBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / "civiccal.sqlite"
        db = sqlite3.connect(self.database)
        import_json_documents(db, *fixture_documents())
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_backup_is_consistent_and_verifiable(self):
        backup = self.root / "backup.sqlite"
        create_backup(self.database, backup)
        verify_database(backup)
        with sqlite3.connect(backup) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM source_events").fetchone()[0], 1)

    def test_backup_refuses_to_overwrite(self):
        backup = self.root / "backup.sqlite"
        backup.write_bytes(b"existing")
        with self.assertRaises(ValueError):
            create_backup(self.database, backup)
        self.assertEqual(backup.read_bytes(), b"existing")


if __name__ == "__main__":
    unittest.main()
