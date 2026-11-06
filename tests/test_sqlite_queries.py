import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.sqlite_storage import import_json_documents
from scripts.sqlite_queries import build_source_calendar, query_events_db
from tests.test_sqlite_storage import fixture_documents


class SQLiteReadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "civiccal.sqlite"
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA foreign_keys=ON")
        registry, state, manifest = fixture_documents()
        # ICS requires a minimally complete event and revision.
        event = state["events"]["identity-1"]
        event["current"].update({
            "title": "Town Meeting", "start": {"value": "2026-11-10", "kind": "date"},
            "time_status": "date_only", "status": "scheduled", "categories": ["Meeting"],
        })
        event["revisions"][0]["observed_at"] = "2026-11-04T12:00:00Z"
        registry["source_records"][0]["name"] = "Town Calendar"
        import_json_documents(db, registry, state, manifest)
        db.close()

    def tearDown(self):
        self.temp.cleanup()

    def test_query_filters_approved_events_and_returns_projection(self):
        result = query_events_db(self.path, source_id="source-a", category="meeting")
        self.assertEqual(result["pagination"]["total"], 1)
        self.assertEqual(result["events"][0]["event"]["title"], "Town Meeting")

    def test_query_date_filter(self):
        result = query_events_db(self.path, start_date="2026-11-11")
        self.assertEqual(result["pagination"]["total"], 0)

    def test_source_calendar_is_scoped_and_approved(self):
        body, summary, modified = build_source_calendar(self.path, "source-a")
        self.assertIn("Town Meeting", body)
        self.assertEqual(summary["published_count"], 1)
        self.assertEqual(modified, "2026-11-04T12:00:00Z")

    def test_unknown_source_fails_not_found(self):
        with self.assertRaises(KeyError):
            build_source_calendar(self.path, "unknown")


if __name__ == "__main__":
    unittest.main()
