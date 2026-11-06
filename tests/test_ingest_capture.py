import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.capture_source import write_capture
from scripts.ingest_capture import IngestError, ingest_capture
from scripts.storage import JsonFileIdentityStateStore

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ID = "village-of-mokena-events"
PAGE_URL = (
    "https://www.mokena.gov/calendarView.aspx"
    "?catid=0&cid=30642&id=0"
)


class IngestCaptureTests(unittest.TestCase):
    def test_archived_village_html_capture_is_ingested_and_idempotent(self):
        payload = (ROOT / "data/fixtures/village-calendar-detail.html").read_bytes()
        captured_at = "2026-11-04T12:00:00+00:00"
        metadata = {
            "format": "civiccal.raw-capture.v1",
            "source_id": SOURCE_ID,
            "source_type": "html",
            "source_url": "https://www.mokena.gov/calendar.aspx",
            "requested_url": PAGE_URL,
            "final_url": PAGE_URL,
            "http_status": 200,
            "captured_at": captured_at,
            "content_sha256": hashlib.sha256(payload).hexdigest(),
            "outcome": "captured",
            "page_role": "detail",
        }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture_path = write_capture(
                SOURCE_ID, payload, metadata, root / "captures"
            )
            state_path = root / "identity-state.json"

            first = ingest_capture(
                SOURCE_ID, capture_path, ROOT / "data/sources.json",
                state_path, adapter="village",
            )
            self.assertEqual(first["parser_event_count"], 1)
            self.assertEqual(first["normalized_event_count"], 1)
            self.assertEqual(first["new_events"], 1)
            self.assertEqual(first["unkeyed_count"], 0)
            self.assertEqual(first["publication"], "not_published; explicit approval manifest remains separate")

            persisted = JsonFileIdentityStateStore(state_path).load_identity_state()
            self.assertEqual(len(persisted["events"]), 1)
            record = next(iter(persisted["events"].values()))
            self.assertEqual(record["source_event_id"], "30642")
            self.assertEqual(record["current"]["title"], "Chamber of Commerce Parade of Lights & Village Tree Lighting Ceremony")
            self.assertEqual(record["current"]["time_status"], "floating")
            self.assertEqual(record["revisions"][0]["revision"], 1)

            second = ingest_capture(
                SOURCE_ID, capture_path, ROOT / "data/sources.json",
                state_path, adapter="village",
            )
            self.assertTrue(second["already_processed"])
            self.assertEqual(second["new_events"], 0)
            self.assertEqual(second["new_revisions"], 0)
            self.assertEqual(len(
                JsonFileIdentityStateStore(state_path).load_identity_state()["events"]
            ), 1)


    def test_archived_ics_capture_is_ingested_and_idempotent_without_registry_mutation(self):
        source_id = "sample-ics-feed"
        source = {
            "id": source_id,
            "source_type": "ics",
            "url": "https://example.org/calendar.ics",
            "access_status": "approved",
            "polling_enabled": False,
            "consent_required": False,
            "terms_reviewed": True,
            "robots_reviewed": True,
            "event_access": "unknown",
        }
        registry = {"source_records": [source]}
        payload = (
            b"BEGIN:VCALENDAR\\r\\nVERSION:2.0\\r\\nPRODID:-//CivicCal Test//EN\\r\\n"
            b"BEGIN:VEVENT\\r\\nUID:sample-meeting@example.org\\r\\n"
            b"DTSTAMP:20261106T120000Z\\r\\nDTSTART:20261110T190000Z\\r\\n"
            b"DTEND:20261110T200000Z\\r\\nSUMMARY:Sample Meeting\\r\\n"
            b"END:VEVENT\\r\\nEND:VCALENDAR\\r\\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry_path = root / "sources.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            original_registry = registry_path.read_bytes()
            metadata = {
                "format": "civiccal.raw-capture.v1",
                "source_id": source_id,
                "source_type": "ics",
                "source_url": source["url"],
                "requested_url": source["url"],
                "final_url": source["url"],
                "http_status": 200,
                "content_type": "application/octet-stream",
                "captured_at": "2026-11-06T12:00:00+00:00",
                "content_sha256": hashlib.sha256(payload).hexdigest(),
                "outcome": "captured",
                "page_role": "feed",
            }
            capture_path = write_capture(
                source_id, payload, metadata, root / "captures"
            )
            state_path = root / "identity-state.json"

            first = ingest_capture(
                source_id, capture_path, registry_path, state_path, adapter="ics"
            )
            self.assertEqual(first["parser_event_count"], 1)
            self.assertEqual(first["normalized_event_count"], 1)
            self.assertEqual(first["new_events"], 1)
            self.assertEqual(first["new_revisions"], 0)
            self.assertEqual(first["publication"],
                             "not_published; explicit approval manifest remains separate")

            persisted = JsonFileIdentityStateStore(state_path).load_identity_state()
            self.assertEqual(len(persisted["events"]), 1)
            record = next(iter(persisted["events"].values()))
            self.assertEqual(record["source_event_id"], "sample-meeting@example.org")
            self.assertEqual(record["revisions"][0]["revision"], 1)

            second = ingest_capture(
                source_id, capture_path, registry_path, state_path, adapter="ics"
            )
            self.assertTrue(second["already_processed"])
            self.assertEqual(second["new_events"], 0)
            self.assertEqual(second["new_revisions"], 0)
            self.assertEqual(registry_path.read_bytes(), original_registry)
            self.assertEqual(
                {key: source[key] for key in (
                    "access_status", "polling_enabled", "consent_required",
                    "terms_reviewed", "robots_reviewed", "event_access",
                )},
                {
                    "access_status": "approved", "polling_enabled": False,
                    "consent_required": False, "terms_reviewed": True,
                    "robots_reviewed": True, "event_access": "unknown",
                },
            )

    def test_unapproved_or_missing_capture_fails_without_creating_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            with self.assertRaises(IngestError):
                ingest_capture(
                    SOURCE_ID, Path(directory) / "missing.json",
                    ROOT / "data/sources.json", state_path, adapter="village",
                )
            self.assertFalse(state_path.exists())


if __name__ == "__main__":
    unittest.main()
