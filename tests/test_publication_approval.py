import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.set_publication_approval import ApprovalError, set_approval
from scripts.sqlite_storage import import_json_documents
from tests.test_sqlite_storage import fixture_documents


class PublicationApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "civiccal.sqlite"
        db = sqlite3.connect(self.database)
        import_json_documents(db, *fixture_documents())
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_revoke_and_approve_are_audited(self):
        result = set_approval(self.database, "source-a", "evt-1",
                              "revoke", "operator", "Publisher request")
        self.assertTrue(result["changed"])
        result = set_approval(self.database, "source-a", "evt-1",
                              "approve", "operator", "Reviewed again")
        self.assertTrue(result["changed"])
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute(
                "SELECT approved FROM publication_approvals WHERE event_id='evt-1'"
            ).fetchone()[0], 1)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM publication_approval_actions"
            ).fetchone()[0], 2)

    def test_wrong_source_cannot_change_event_approval(self):
        with self.assertRaises(ApprovalError):
            set_approval(self.database, "source-b", "evt-1", "revoke", "operator")
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute(
                "SELECT approved FROM publication_approvals WHERE event_id='evt-1'"
            ).fetchone()[0], 1)

    def test_repeating_same_action_is_idempotent(self):
        result = set_approval(self.database, "source-a", "evt-1",
                              "approve", "operator")
        self.assertFalse(result["changed"])
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM publication_approval_actions"
            ).fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
