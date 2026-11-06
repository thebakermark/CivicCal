import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

from scripts.sqlite_storage import import_json_documents
from scripts.serve_sqlite_api import make_handler
from tests.test_sqlite_storage import fixture_documents


class SQLiteAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "civiccal.sqlite"
        db = sqlite3.connect(self.path)
        registry, state, manifest = fixture_documents()
        event = state["events"]["identity-1"]
        event["current"].update({
            "title": "Town Meeting", "start": {"value": "2026-11-10", "kind": "date"},
            "time_status": "date_only", "status": "scheduled", "categories": ["Meeting"],
        })
        event["revisions"][0]["observed_at"] = "2026-11-04T12:00:00Z"
        import_json_documents(db, registry, state, manifest)
        db.close()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.path))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def test_health_reports_sqlite_storage(self):
        with urlopen(self.base + "/health") as response:
            value = json.loads(response.read())
        self.assertEqual(value["storage"], "sqlite")

    def test_json_api_reads_approved_database_records(self):
        with urlopen(self.base + "/api/v1/events?source_id=source-a") as response:
            value = json.loads(response.read())
        self.assertEqual(value["pagination"]["total"], 1)
        self.assertEqual(value["events"][0]["event"]["title"], "Town Meeting")

    def test_source_ics_reads_database(self):
        with urlopen(self.base + "/calendars/sources/source-a.ics") as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.headers.get_content_type(), "text/calendar")
        self.assertIn("Town Meeting", body)

    def test_write_methods_are_disabled(self):
        from urllib.request import Request
        with self.assertRaises(HTTPError) as caught:
            urlopen(Request(self.base + "/api/v1/events", data=b"{}", method="POST"))
        self.assertEqual(caught.exception.code, 405)


if __name__ == "__main__":
    unittest.main()
