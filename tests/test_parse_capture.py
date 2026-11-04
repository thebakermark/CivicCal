import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.parse_capture import (
    HandoffError,
    capture_summary,
    load_capture,
    load_registry_source,
    parse_payload,
    select_adapter,
)
from scripts.capture_source import write_capture

ROOT = Path(__file__).resolve().parents[1]


class ParseCaptureTests(unittest.TestCase):
    def make_capture(self, folder, source_id, payload, final_url, source_type="html", status=200):
        digest = hashlib.sha256(payload).hexdigest() if status == 200 else None
        metadata = {
            "format": "civiccal.raw-capture.v1",
            "source_id": source_id,
            "source_type": source_type,
            "requested_url": final_url,
            "final_url": final_url,
            "http_status": status,
            "captured_at": "2026-11-04T12:00:00+00:00",
            "content_sha256": digest,
            "outcome": "captured" if status == 200 else "not_modified",
        }
        path = write_capture(source_id, payload if status == 200 else None, metadata, Path(folder))
        return path

    def test_registry_source_lookup_rejects_invalid_registry_shapes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sources.json"
            for content in ["[]", '{"organizations": []}', '{"source_records": [null]}']:
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(HandoffError):
                    load_registry_source(path, "source-a")

    def test_registry_source_lookup_requires_exactly_one_id(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sources.json"
            path.write_text(json.dumps({"source_records": [
                {"id": "source-a"}, {"id": "source-a"}
            ]}), encoding="utf-8")
            with self.assertRaisesRegex(HandoffError, "found 2"):
                load_registry_source(path, "source-a")

    def test_capture_summary_preserves_outcome_and_page_provenance(self):
        metadata = {
            "captured_at": "2026-11-04T12:00:00Z",
            "content_sha256": "a" * 64,
            "final_url": "https://example.test/listing",
            "requested_url": "https://example.test/listing",
            "source_url": "https://example.test/calendar",
            "http_status": 200,
            "outcome": "captured",
            "page_role": "listing",
        }
        summary = capture_summary(metadata, Path("capture.json"))
        self.assertEqual(summary["outcome"], "captured")
        self.assertEqual(summary["http_status"], 200)
        self.assertEqual(summary["page_role"], "listing")
        self.assertEqual(summary["source_url"], "https://example.test/calendar")

    def test_ics_capture_dispatches_to_existing_ics_parser(self):
        payload = (ROOT / "data/fixtures/sample-community.ics").read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            metadata_path = self.make_capture(
                folder, "sample-school-ics", payload,
                "https://example.org/events.ics", source_type="ics",
            )
            metadata, archived = load_capture(metadata_path, "sample-school-ics")
            adapter = select_adapter("auto", "ics")
            parsed = parse_payload(archived, adapter, "sample-school-ics", metadata["final_url"])
        self.assertEqual(adapter, "ics")
        self.assertEqual(parsed["event_count"], 2)
        self.assertEqual(parsed["events"][0]["source_id"], "sample-school-ics")

    def test_generic_jsonld_capture_uses_shared_html_parser(self):
        html = b'''<html><script type="application/ld+json">{"@type":"Event","name":"Library story time","startDate":"2026-11-10T10:00:00-06:00"}</script></html>'''
        parsed = parse_payload(html, "jsonld", "library-events", "https://example.org/events")
        self.assertEqual(parsed["event_count"], 1)
        self.assertEqual(parsed["events"][0]["source_id"], "library-events")

    def test_park_adapter_uses_registry_source_id(self):
        html = (ROOT / "data/fixtures/mokena-park-upcoming.html").read_bytes()
        parsed = parse_payload(
            html, "mokena_park", "mokena-park-district-events",
            "https://www.mokenapark.com/upcoming-events-2/",
        )
        self.assertEqual(parsed["event_count"], 3)
        self.assertEqual(parsed["source_id"], "mokena-park-district-events")
        self.assertTrue(all(e["source_id"] == "mokena-park-district-events" for e in parsed["events"]))

    def test_village_adapter_handles_event_detail_and_preserves_source_id(self):
        html = (ROOT / "data/fixtures/village-calendar-detail.html").read_bytes()
        url = "https://www.mokena.gov/calendarView.aspx?catid=0&cid=30642&id=0"
        parsed = parse_payload(html, "village", "village-of-mokena-events", url)
        self.assertEqual(parsed["page_type"], "event_detail")
        self.assertEqual(parsed["event_count"], 1)
        self.assertEqual(parsed["events"][0]["source_id"], "village-of-mokena-events")

    def test_auto_dispatch_does_not_guess_unknown_formats(self):
        with self.assertRaisesRegex(HandoffError, "No automatic parser"):
            select_adapter("auto", "xml")

    def test_adapter_format_mismatch_is_rejected(self):
        with self.assertRaisesRegex(HandoffError, "requires an ICS"):
            select_adapter("ics", "html")

    def test_wrong_source_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_capture(folder, "source-a", b"hello", "https://example.org")
            with self.assertRaisesRegex(HandoffError, "does not match"):
                load_capture(path, "source-b")

    def test_tampered_raw_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_capture(folder, "source-a", b"original", "https://example.org")
            metadata = json.loads(path.read_text(encoding="utf-8"))
            (path.parent / metadata["raw_payload_file"]).write_bytes(b"modified")
            with self.assertRaisesRegex(HandoffError, "SHA-256"):
                load_capture(path, "source-a")

    def test_304_metadata_cannot_be_parsed_without_a_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_capture(
                folder, "source-a", b"", "https://example.org", status=304,
            )
            with self.assertRaisesRegex(HandoffError, "Only successful captures"):
                load_capture(path, "source-a")


if __name__ == "__main__":
    unittest.main()
