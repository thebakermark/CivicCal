import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone

from scripts.report_source_health import build_report


class SourceHealthReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.registry = self.root / "sources.json"
        self.archive = self.root / "captures"
        self.archive.mkdir()
        self.registry.write_text(json.dumps({
            "source_records": [
                {"id": "open", "organization_id": "org", "name": "Open",
                 "source_type": "ics", "access_status": "approved",
                 "terms_reviewed": True, "robots_reviewed": True,
                 "polling_enabled": False},
                {"id": "review", "organization_id": "org", "name": "Review",
                 "source_type": "html", "access_status": "review_required",
                 "polling_enabled": False},
                {"id": "consent", "organization_id": "org", "name": "Consent",
                 "source_type": "html", "access_status": "blocked",
                 "consent_required": True, "consent_granted": False,
                 "polling_enabled": False},
            ]
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_reports_policy_states_without_network_access(self):
        report = build_report(self.registry, self.archive)
        self.assertFalse(report["network_access"])
        self.assertEqual(report["summary"]["source_count"], 3)
        states = {item["source_id"]: item["policy_state"] for item in report["sources"]}
        self.assertEqual(states, {
            "consent": "consent_required",
            "open": "approved",
            "review": "review_required",
        })

    def test_validates_archived_payload_hash(self):
        folder = self.archive / "open"
        folder.mkdir()
        payload = b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"
        import hashlib
        digest = hashlib.sha256(payload).hexdigest()
        (folder / f"{digest}.bin").write_bytes(payload)
        (folder / "capture-20261104T120000Z-" + Path("x")).exists() if False else None
        metadata = {
            "format": "civiccal.raw-capture.v1",
            "source_id": "open",
            "captured_at": "2026-11-04T12:00:00+00:00",
            "outcome": "captured",
            "http_status": 200,
            "content_type": "text/calendar",
            "content_length": len(payload),
            "content_sha256": digest,
            "raw_payload_file": f"{digest}.bin",
            "page_role": "feed",
        }
        (folder / "capture-test.json").write_text(json.dumps(metadata), encoding="utf-8")
        report = build_report(self.registry, self.archive)
        source = next(item for item in report["sources"] if item["source_id"] == "open")
        self.assertEqual(source["capture_count"], 1)
        self.assertEqual(source["latest_capture"]["content_sha256"], digest)
        self.assertEqual(report["warnings"], [])

    def test_missing_archived_payload_is_a_warning(self):
        folder = self.archive / "open"
        folder.mkdir()
        metadata = {
            "format": "civiccal.raw-capture.v1",
            "source_id": "open",
            "captured_at": "2026-11-04T12:00:00+00:00",
            "outcome": "captured",
            "content_sha256": "a" * 64,
            "raw_payload_file": "missing.bin",
        }
        (folder / "capture-test.json").write_text(json.dumps(metadata), encoding="utf-8")
        report = build_report(self.registry, self.archive)
        self.assertTrue(any("payload missing" in warning for warning in report["warnings"]))

    def test_duplicate_source_ids_are_rejected(self):
        self.registry.write_text(json.dumps({"source_records": [{"id": "same"}, {"id": "same"}]}))
        with self.assertRaises(Exception):
            build_report(self.registry, self.archive)


if __name__ == "__main__":
    unittest.main()
