import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.sqlite_storage import SQLiteIdentityStateStore, import_json_documents
from tests.test_sqlite_storage import fixture_documents
from tests.test_track_event_identity import event, normalized


class SQLiteIngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "civiccal.sqlite"
        registry, _, _ = fixture_documents()
        registry["source_records"].append({
            "id": "source-b", "organization_id": "org-a",
            "consent_granted": False, "polling_enabled": False,
        })
        empty_state = {
            "format": "civiccal.identity-state.v1", "events": {},
            "observations": [], "unkeyed_observations": [],
            "processed_captures": [], "presence_observations": [],
        }
        manifest = {"format": "civiccal.publication-manifest.v1",
                    "approved_event_ids": []}
        db = sqlite3.connect(self.database)
        import_json_documents(db, registry, empty_state, manifest)
        db.close()
        self.store = SQLiteIdentityStateStore(self.database)

    def tearDown(self):
        self.temp.cleanup()

    def counts(self):
        with sqlite3.connect(self.database) as db:
            return {
                "events": db.execute("SELECT COUNT(*) FROM source_events").fetchone()[0],
                "observations": db.execute("SELECT COUNT(*) FROM event_observations").fetchone()[0],
                "revisions": db.execute("SELECT COUNT(*) FROM event_revisions").fetchone()[0],
                "processed": db.execute("SELECT COUNT(*) FROM processed_captures").fetchone()[0],
                "approvals": db.execute("SELECT COUNT(*) FROM publication_approvals").fetchone()[0],
            }

    def test_ingest_is_atomic_and_keeps_publication_separate(self):
        result = self.store.ingest_normalized(
            normalized([event()], source="source-a", capture="capture-1"),
            observed_at="2026-11-04T12:00:00Z",
        )
        self.assertEqual(result["new_events"], 1)
        self.assertEqual(self.counts(), {
            "events": 1, "observations": 1, "revisions": 1,
            "processed": 1, "approvals": 0,
        })

    def test_same_capture_is_idempotent(self):
        document = normalized([event()], source="source-a", capture="capture-1")
        self.store.ingest_normalized(document)
        result = self.store.ingest_normalized(document)
        self.assertTrue(result["already_processed"])
        self.assertEqual(self.counts()["observations"], 1)
        self.assertEqual(self.counts()["revisions"], 1)

    def test_new_capture_appends_observation_and_revision_with_stable_event_id(self):
        first = self.store.ingest_normalized(
            normalized([event()], source="source-a", capture="capture-1")
        )
        second = self.store.ingest_normalized(
            normalized([event(title="Updated meeting")], source="source-a", capture="capture-2")
        )
        self.assertEqual(first["events"][0]["event_id"], second["events"][0]["event_id"])
        self.assertEqual(self.counts()["events"], 1)
        self.assertEqual(self.counts()["observations"], 2)
        self.assertEqual(self.counts()["revisions"], 2)

    def test_identity_is_scoped_to_source(self):
        self.store.ingest_normalized(normalized([event()], source="source-a", capture="a"))
        self.store.ingest_normalized(normalized([event()], source="source-b", capture="b"))
        self.assertEqual(self.counts()["events"], 2)

    def test_duplicate_identity_conflict_is_retained_without_event_creation(self):
        result = self.store.ingest_normalized(
            normalized([event(), event(title="Conflicting copy")],
                       source="source-a", capture="conflict")
        )
        self.assertEqual(len(result["identity_conflicts"]), 1)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM identity_conflicts").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM source_events").fetchone()[0], 0)

    def test_archived_capture_provenance_is_registered(self):
        metadata = {
            "captured_at": "2026-11-04T12:00:00Z",
            "requested_url": "https://example.test/events.ics",
            "final_url": "https://example.test/events.ics",
            "http_status": 200,
            "content_type": "text/calendar",
            "etag": '"capture-1"',
            "last_modified": None,
            "content_sha256": "capture-1",
            "content_length": 123,
            "outcome": "captured",
        }
        self.store.ingest_normalized(
            normalized([event()], source="source-a", capture="capture-1"),
            capture_metadata=metadata,
            archive_uri="/archive/source-a/capture-1.json",
        )
        with sqlite3.connect(self.database) as db:
            row = db.execute(
                "SELECT source_id, capture_key, payload_sha256, archive_uri FROM captures"
            ).fetchone()
        self.assertEqual(row, (
            "source-a", "capture-1", "capture-1", "/archive/source-a/capture-1.json"
        ))

    def test_source_authorization_flags_are_not_changed_by_ingestion(self):
        self.store.ingest_normalized(normalized([event()], source="source-a", capture="capture-1"))
        with sqlite3.connect(self.database) as db:
            auth = db.execute(
                "SELECT authorization_json FROM sources WHERE source_id='source-a'"
            ).fetchone()[0]
        self.assertIn('"consent_granted":false', auth)
        self.assertIn('"polling_enabled":false', auth)


if __name__ == "__main__":
    unittest.main()
