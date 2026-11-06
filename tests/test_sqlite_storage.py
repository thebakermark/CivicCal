import sqlite3
import unittest

from scripts.sqlite_storage import MigrationError, import_json_documents


def fixture_documents():
    registry = {
        "organizations": [{"id": "org-a", "name": "Town"}],
        "source_records": [{"id": "source-a", "organization_id": "org-a",
                            "consent_granted": False, "polling_enabled": False}],
    }
    observation = {
        "observation_id": "obs-1", "source_id": "source-a",
        "source_event_id": "publisher-1", "identity_key": "identity-1",
        "capture_key": "capture-1", "observed_at": "2026-11-04T12:00:00Z",
        "material_fingerprint": "fingerprint-1",
        "event": {"title": "Meeting", "source_record": {"uid": "publisher-1"}},
    }
    revision = {
        "revision": 1, "fingerprint": "fingerprint-1",
        "observed_at": "2026-11-04T12:00:00Z", "observation_id": "obs-1",
        "change_type": "created", "values": {"title": "Meeting"},
    }
    event = {
        "event_id": "evt-1", "identity_key": "identity-1", "source_id": "source-a",
        "source_event_id": "publisher-1", "current": {"title": "Meeting"},
        "current_fingerprint": "fingerprint-1", "current_revision_number": 1,
        "observation_ids": ["obs-1"], "revisions": [revision],
        "lifecycle_history": [], "missing_observation_history": [],
        "presence_status": "present", "missing_snapshot_count": 0,
    }
    state = {
        "format": "civiccal.identity-state.v1", "events": {"identity-1": event},
        "observations": [observation], "unkeyed_observations": [],
        "processed_captures": ["token-1"], "presence_observations": [],
    }
    manifest = {"format": "civiccal.publication-manifest.v1",
                "approved_event_ids": ["evt-1"]}
    return registry, state, manifest


class SQLiteMigrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys=ON")

    def tearDown(self):
        self.connection.close()

    def test_import_preserves_identity_history_and_approval(self):
        counts = import_json_documents(self.connection, *fixture_documents())
        self.assertEqual(counts["events"], 1)
        self.assertEqual(counts["observations"], 1)
        self.assertEqual(counts["revisions"], 1)
        self.assertEqual(counts["publication_approvals"], 1)
        row = self.connection.execute(
            "SELECT event_id, identity_key, current_event_json FROM source_events"
        ).fetchone()
        self.assertEqual(row[0], "evt-1")
        self.assertEqual(row[1], "identity-1")
        self.assertIn("Meeting", row[2])

    def test_authorization_flags_are_preserved_exactly(self):
        import_json_documents(self.connection, *fixture_documents())
        row = self.connection.execute(
            "SELECT authorization_json FROM sources WHERE source_id='source-a'"
        ).fetchone()
        self.assertIn('"consent_granted":false', row[0])
        self.assertIn('"polling_enabled":false', row[0])

    def test_missing_observation_reference_rolls_back_entire_import(self):
        registry, state, manifest = fixture_documents()
        state["events"]["identity-1"]["observation_ids"] = ["missing"]
        with self.assertRaises(MigrationError):
            import_json_documents(self.connection, registry, state, manifest)
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM source_events"
        ).fetchone()[0], 0)
        self.assertEqual(self.connection.execute(
            "SELECT COUNT(*) FROM organizations"
        ).fetchone()[0], 0)

    def test_unknown_source_rejected(self):
        registry, state, manifest = fixture_documents()
        state["events"]["identity-1"]["source_id"] = "not-registered"
        with self.assertRaises(MigrationError):
            import_json_documents(self.connection, registry, state, manifest)

    def test_duplicate_approval_rejected(self):
        registry, state, manifest = fixture_documents()
        manifest["approved_event_ids"] = ["evt-1", "evt-1"]
        with self.assertRaises(MigrationError):
            import_json_documents(self.connection, registry, state, manifest)


if __name__ == "__main__":
    unittest.main()
