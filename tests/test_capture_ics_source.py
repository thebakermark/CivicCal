import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

from scripts.capture_ics_source import (
    ICSCoordinatorError,
    coordinate_ics_capture,
)
from scripts.capture_source import load_source

FEED = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//CivicCal Test//EN
BEGIN:VEVENT
UID:school-board-20261110@example.test
DTSTAMP:20261104T120000Z
DTSTART;TZID=America/Chicago:20261110T190000
DTEND;TZID=America/Chicago:20261110T200000
SUMMARY:School Board Meeting
LOCATION:District Office
STATUS:CONFIRMED
END:VEVENT
BEGIN:VEVENT
UID:thanksgiving-2026@example.test
DTSTAMP:20261104T120000Z
DTSTART;VALUE=DATE:20261126
DTEND;VALUE=DATE:20261127
SUMMARY:Thanksgiving Break
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""


class FakeResponse:
    def __init__(self, body, url, status=200, content_type="text/calendar; charset=utf-8"):
        self.body = body
        self.url = url
        self.status = status
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["ETag"] = '"fixture-ics"'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, size=-1):
        return self.body[:size]


class CaptureICSCoordinatorTests(unittest.TestCase):
    def source(self, **overrides):
        value = {
            "id": "summit-hill-sd161-events-ical",
            "source_type": "ics",
            "url": "https://www.summithill.org/apps/events/ical/?id=0",
            "access_status": "approved",
            "terms_reviewed": True,
            "robots_reviewed": True,
            "polling_enabled": False,
        }
        value.update(overrides)
        return value

    def policies(self, folder, allow_complete=False):
        path = Path(folder) / "policies.json"
        path.write_text(json.dumps({
            "format": "civiccal.source-completeness-policies.v1",
            "profiles": [{
                "source_id": "summit-hill-sd161-events-ical",
                "profile_id": "summit-hill-test",
                "scope": "District Events feed only.",
                "pagination_strategy": "single_feed",
                "required_page_roles": ["feed"],
                "require_detail_link_reconciliation": False,
                "allow_complete_snapshot": allow_complete,
                "reason_disabled": "Feed scope has not yet been validated.",
                "allowed_hosts": ["www.summithill.org"],
                "allowed_paths": ["/apps/events/ical/"],
            }],
        }), encoding="utf-8")
        return path

    def opener_factory(self, body=FEED, final_url=None, failure=None,
                       content_type="text/calendar; charset=utf-8"):
        def factory(source, policies_path):
            def open_request(request, timeout=20):
                if failure:
                    raise failure
                return FakeResponse(body, final_url or request.full_url,
                                    content_type=content_type)
            return open_request
        return factory

    def test_captures_archives_parses_and_normalizes_ics_feed(self):
        with tempfile.TemporaryDirectory() as folder:
            result = coordinate_ics_capture(
                self.source(), self.policies(folder), Path(folder) / "archive",
                opener_factory=self.opener_factory(),
            )
            self.assertEqual(result["event_count"], 2)
            self.assertEqual(result["parser_format"], "civiccal.ics.v1")
            self.assertEqual(result["snapshot"]["completeness"], "unknown")
            self.assertEqual(result["summary"]["publisher_id_count"], 2)
            self.assertEqual(result["events"][0]["capture"]["page_role"], "feed")
            self.assertEqual(result["events"][0]["time_status"], "zoned")
            self.assertTrue(any(event["all_day"] for event in result["events"]))
            self.assertFalse(result["coordinator"]["automatic_polling_enabled"])
            self.assertFalse(result["coordinator"]["published"])
            archive = list((Path(folder) / "archive").rglob("*.bin"))
            self.assertEqual(len(archive), 1)
            self.assertEqual(archive[0].read_bytes(), FEED)

    def test_verified_policy_can_mark_valid_nonempty_single_feed_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            result = coordinate_ics_capture(
                self.source(), self.policies(folder, allow_complete=True),
                Path(folder) / "archive", opener_factory=self.opener_factory(),
            )
            self.assertEqual(result["snapshot"]["completeness"], "complete")
            self.assertEqual(result["snapshot"]["blockers"], [])

    def test_empty_feed_requires_explicit_operator_confirmation(self):
        empty_feed = b"BEGIN:VCALENDAR\nVERSION:2.0\nEND:VCALENDAR\n"
        with tempfile.TemporaryDirectory() as folder:
            policies = self.policies(folder, allow_complete=True)
            without_confirmation = coordinate_ics_capture(
                self.source(), policies, Path(folder) / "archive-a",
                opener_factory=self.opener_factory(body=empty_feed),
            )
            self.assertEqual(without_confirmation["snapshot"]["completeness"], "partial")
            with_confirmation = coordinate_ics_capture(
                self.source(), policies, Path(folder) / "archive-b",
                opener_factory=self.opener_factory(body=empty_feed),
                empty_snapshot_confirmed=True,
            )
            self.assertEqual(with_confirmation["snapshot"]["completeness"], "complete")
            self.assertTrue(with_confirmation["snapshot"]["empty_snapshot_confirmed"])

    def test_policy_can_never_be_overridden_by_cli_empty_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            result = coordinate_ics_capture(
                self.source(), self.policies(folder, allow_complete=False),
                Path(folder) / "archive", opener_factory=self.opener_factory(),
                empty_snapshot_confirmed=True,
            )
            self.assertEqual(result["snapshot"]["completeness"], "unknown")
            self.assertTrue(any("not yet been validated" in item
                                for item in result["snapshot"]["blockers"]))

    def test_parser_warnings_make_snapshot_partial(self):
        feed = FEED.replace(b"END:VEVENT", b"X-UNKNOWN;BROKEN\nEND:VEVENT", 1)
        with tempfile.TemporaryDirectory() as folder:
            result = coordinate_ics_capture(
                self.source(), self.policies(folder, allow_complete=True),
                Path(folder) / "archive", opener_factory=self.opener_factory(body=feed),
            )
            self.assertGreater(result["summary"]["parser_warning_count"], 0)
            self.assertEqual(result["snapshot"]["completeness"], "partial")


    def test_valid_ics_is_accepted_when_server_uses_generic_octet_stream(self):
        with tempfile.TemporaryDirectory() as folder:
            result = coordinate_ics_capture(
                self.source(), self.policies(folder), Path(folder) / "archive",
                opener_factory=self.opener_factory(content_type="application/octet-stream"),
            )
            self.assertEqual(result["event_count"], 2)
            metadata_path = Path(result["coordinator"]["raw_capture_metadata"])
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["content_type"], "application/octet-stream")
            self.assertEqual(metadata["content_sha256"], result["events"][0]["capture"]["content_sha256"])

    def test_registered_calendar_mime_type_is_preserved_in_capture_metadata(self):
        with tempfile.TemporaryDirectory() as folder:
            result = coordinate_ics_capture(
                self.source(), self.policies(folder), Path(folder) / "archive",
                opener_factory=self.opener_factory(content_type="text/calendar; charset=utf-8"),
            )
            metadata_path = Path(result["coordinator"]["raw_capture_metadata"])
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["content_type"], "text/calendar; charset=utf-8")
            self.assertEqual(result["event_count"], 2)

    def test_non_calendar_response_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ICSCoordinatorError, "VCALENDAR"):
                coordinate_ics_capture(
                    self.source(), self.policies(folder), Path(folder) / "archive",
                    opener_factory=self.opener_factory(body=b"<html>not a calendar</html>"),
                )

    def test_redirect_outside_source_allowlist_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(Exception, "allowlist"):
                coordinate_ics_capture(
                    self.source(), self.policies(folder), Path(folder) / "archive",
                    opener_factory=self.opener_factory(final_url="https://evil.example/feed.ics"),
                )

    def test_304_is_archived_but_not_treated_as_a_new_snapshot(self):
        headers = Message()
        headers["ETag"] = '"old"'
        not_modified = HTTPError(
            "https://www.summithill.org/apps/events/ical/?id=0",
            304, "Not Modified", headers, None,
        )
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ICSCoordinatorError, "HTTP 304"):
                coordinate_ics_capture(
                    self.source(), self.policies(folder), Path(folder) / "archive",
                    opener_factory=self.opener_factory(failure=not_modified),
                )
            metadata = list((Path(folder) / "archive").rglob("not-modified-*.json"))
            self.assertEqual(len(metadata), 1)

    def test_non_ics_source_is_rejected_before_network(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ICSCoordinatorError, "only registered ICS"):
                coordinate_ics_capture(
                    self.source(source_type="html"), self.policies(folder),
                    Path(folder) / "archive",
                    opener_factory=lambda *_: self.fail("network must not be called"),
                )

    def test_registered_source_gates_still_block_unapproved_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = Path(folder) / "sources.json"
            source = self.source(access_status="review_required")
            registry.write_text(json.dumps({"source_records": [source]}), encoding="utf-8")
            with self.assertRaisesRegex(Exception, "not approved"):
                load_source(registry, source["id"])


if __name__ == "__main__":
    unittest.main()
