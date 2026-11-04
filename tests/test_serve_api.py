import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer

from scripts.serve_api import make_handler


def documents():
    event = {
        "event_id": "evt-public",
        "source_id": "library",
        "current": {
            "title": "Public Storytime",
            "description": "Books and songs",
            "start": {"value": "2026-11-10", "kind": "date"},
            "end": None,
            "time_status": "date_only",
            "status": "scheduled",
            "categories": ["Storytime"],
        },
        "revisions": [{"revision": 1, "observed_at": "2026-11-04T18:00:00Z"}],
    }
    private = {
        "event_id": "evt-private",
        "source_id": "internal",
        "current": {
            "title": "Internal Draft",
            "start": {"value": "2026-11-11", "kind": "date"},
            "time_status": "date_only",
            "status": "scheduled",
        },
        "revisions": [{"revision": 1, "observed_at": "2026-11-04T18:00:00Z"}],
    }
    state = {"format": "civiccal.identity-state.v1", "events": {"a": event, "b": private}}
    manifest = {
        "format": "civiccal.publication-manifest.v1",
        "calendar_name": "CivicCal Test",
        "approved_event_ids": ["evt-public"],
    }
    return state, manifest


class ServeAPITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        state, manifest = documents()
        self.state_path = root / "state.json"
        self.manifest_path = root / "manifest.json"
        self.state_path.write_text(json.dumps(state), encoding="utf-8")
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), make_handler(self.state_path, self.manifest_path)
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def test_events_endpoint_returns_only_approved_events(self):
        with urlopen(self.base + "/api/v1/events") as response:
            payload = json.loads(response.read())
            self.assertEqual(response.status, 200)
        self.assertEqual([item["event_id"] for item in payload["events"]], ["evt-public"])

    def test_events_endpoint_supports_filters(self):
        with urlopen(self.base + "/api/v1/events?source_id=library&category=storytime") as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["pagination"]["total"], 1)

    def test_ics_endpoint_returns_calendar_content(self):
        with urlopen(self.base + "/calendars/community.ics") as response:
            body = response.read().decode("utf-8")
            self.assertEqual(response.headers.get_content_type(), "text/calendar")
        self.assertIn("UID:evt-public@civiccal", body)
        self.assertNotIn("evt-private", body)

    def test_etag_returns_not_modified_for_unchanged_feed(self):
        with urlopen(self.base + "/calendars/community.ics") as response:
            etag = response.headers["ETag"]
        request = Request(self.base + "/calendars/community.ics", headers={"If-None-Match": etag})
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        self.assertEqual(caught.exception.code, 304)

    def test_invalid_query_is_a_client_error(self):
        with urlopen(self.base + "/api/v1/events?limit=101") as response:
            payload = json.loads(response.read())
            self.assertEqual(response.status, 400)
        self.assertEqual(payload["error"], "invalid_request")

    def test_unknown_path_is_not_found(self):
        with urlopen(self.base + "/not-a-route") as response:
            self.assertEqual(response.status, 404)

    def test_health_and_openapi_are_available(self):
        with urlopen(self.base + "/health") as response:
            self.assertEqual(json.loads(response.read())["status"], "ok")
        with urlopen(self.base + "/openapi.json") as response:
            self.assertIn("/api/v1/events", json.loads(response.read())["paths"])


if __name__ == "__main__":
    unittest.main()
