import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from urllib.request import Request

from scripts.capture_coordinator import (
    CoordinationError,
    coordinate_village_capture,
)


LISTING_ONE = b"""<html><body>
<a href="https://mokenail.municipalone.com/calendarView.aspx?cid=1001">Community Day</a>
<a rel="next" href="calendar.aspx?page=2">Next</a>
</body></html>"""
LISTING_TWO = b"""<html><body>
<a href="https://mokenail.municipalone.com/calendarView.aspx?cid=1002">Board Meeting</a>
<a rel="last" href="https://www.mokena.gov/calendar.aspx?page=2">Last</a>
</body></html>"""
DETAIL_ONE = b"""<html><body><nav>Home Government Residents Economic Development How Do I?</nav><main>
<div>Community Day</div><div>Event Date:</div><div>Saturday, June 13, 2026</div>
<div>Event Time:</div><div>10:00 AM - 2:00 PM</div><div>Location:</div><div>Village Hall</div>
<div>Details:</div><div>Community gathering</div></main></body></html>"""
DETAIL_TWO = b"""<html><body><nav>Home Government Residents Economic Development How Do I?</nav><main>
<div>Board Meeting</div><div>Event Date:</div><div>Monday, June 15, 2026</div>
<div>Event Time:</div><div>7:00 PM - 8:00 PM</div><div>Location:</div><div>Village Hall</div>
<div>Details:</div></main></body></html>"""


class FakeResponse:
    def __init__(self, body, url):
        self.body = body
        self.url = url
        self.status = 200
        self.headers = Message()
        self.headers["Content-Type"] = "text/html; charset=utf-8"
        self.headers["ETag"] = '"fixture"'

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, size=-1):
        return self.body[:size]


class CaptureCoordinatorTests(unittest.TestCase):
    def source(self):
        return {
            "id": "village-of-mokena-events",
            "source_type": "html",
            "url": "https://www.mokena.gov/calendar.aspx",
            "access_status": "approved",
            "terms_reviewed": True,
            "robots_reviewed": True,
            "polling_enabled": False,
        }

    def policies(self, folder, allow_complete=True):
        path = Path(folder) / "policies.json"
        path.write_text(json.dumps({
            "format": "civiccal.source-completeness-policies.v1",
            "profiles": [{
                "source_id": "village-of-mokena-events",
                "profile_id": "village-test",
                "scope": "Test calendar listing and linked event details.",
                "pagination_strategy": "rel_next",
                "required_page_roles": ["listing", "detail"],
                "require_detail_link_reconciliation": True,
                "allow_complete_snapshot": allow_complete,
                "allowed_hosts": ["www.mokena.gov", "mokenail.municipalone.com"],
                "allowed_paths": ["/calendar.aspx", "/calendarView.aspx"],
            }],
        }), encoding="utf-8")
        return path

    def opener_factory(self, fail_url=None):
        responses = {
            "https://www.mokena.gov/calendar.aspx": LISTING_ONE,
            "https://www.mokena.gov/calendar.aspx?page=2": LISTING_TWO,
            "https://mokenail.municipalone.com/calendarView.aspx?cid=1001": DETAIL_ONE,
            "https://mokenail.municipalone.com/calendarView.aspx?cid=1002": DETAIL_TWO,
        }

        def factory(source, policies_path):
            def open_request(request: Request, timeout=20):
                url = request.full_url
                if url == fail_url:
                    raise OSError("fixture network failure")
                return FakeResponse(responses[url], url)
            return open_request
        return factory

    def test_follows_next_page_and_captures_every_detail(self):
        with tempfile.TemporaryDirectory() as folder:
            policies = self.policies(folder)
            result = coordinate_village_capture(
                self.source(), policies, Path(folder) / "archive",
                opener_factory=self.opener_factory(),
            )
            self.assertEqual(result["summary"]["listing_pages"], 2)
            self.assertEqual(result["summary"]["detail_pages"], 2)
            self.assertEqual(result["event_count"], 2)
            self.assertEqual(
                {event["source_event_id"] for event in result["events"]},
                {"1001", "1002"},
            )
            self.assertEqual(result["snapshot"]["completeness"], "complete")
            self.assertTrue(result["coordinator"]["automatic_polling_enabled"] is False)
            self.assertTrue(result["coordinator"]["published"] is False)
            self.assertEqual(len(list((Path(folder) / "archive").rglob("*.bin"))), 4)

    def test_missing_explicit_terminal_page_signal_prevents_complete_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            policies = self.policies(folder)
            original_factory = self.opener_factory()

            def no_last_factory(source, policies_path):
                def open_request(request, timeout=20):
                    response = original_factory(source, policies_path)(request, timeout)
                    if request.full_url == "https://www.mokena.gov/calendar.aspx?page=2":
                        response.body = response.body.replace(
                            b'<a rel="last" href="https://www.mokena.gov/calendar.aspx?page=2">Last</a>', b""
                        )
                    return response
                return open_request

            result = coordinate_village_capture(
                self.source(), policies, Path(folder) / "archive",
                opener_factory=no_last_factory,
            )
            self.assertEqual(result["snapshot"]["completeness"], "partial")
            self.assertTrue(any("terminal page" in blocker
                                for blocker in result["snapshot"]["blockers"]))

    def test_live_profile_disabled_keeps_snapshot_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            policies = self.policies(folder, allow_complete=False)
            result = coordinate_village_capture(
                self.source(), policies, Path(folder) / "archive",
                opener_factory=self.opener_factory(),
            )
            self.assertEqual(result["snapshot"]["completeness"], "unknown")
            self.assertTrue(result["snapshot"]["blockers"])

    def test_failed_detail_page_prevents_complete_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            policies = self.policies(folder)
            result = coordinate_village_capture(
                self.source(), policies, Path(folder) / "archive",
                opener_factory=self.opener_factory(
                    "https://mokenail.municipalone.com/calendarView.aspx?cid=1002"
                ),
            )
            self.assertEqual(result["snapshot"]["completeness"], "partial")
            self.assertTrue(any("Detail page failed" in warning for warning in result["parser_warnings"]))

    def test_page_limit_leaves_next_page_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            policies = self.policies(folder)
            result = coordinate_village_capture(
                self.source(), policies, Path(folder) / "archive",
                max_pages=1, opener_factory=self.opener_factory(),
            )
            self.assertEqual(result["summary"]["listing_pages"], 1)
            self.assertEqual(result["snapshot"]["completeness"], "partial")
            self.assertTrue(result["coordinator"]["manifest"]["pagination"]["pending_next_urls"])

    def test_other_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            policies = self.policies(folder)
            source = self.source()
            source["id"] = "another-source"
            with self.assertRaisesRegex(CoordinationError, "Village"):
                coordinate_village_capture(source, policies, Path(folder) / "archive")


if __name__ == "__main__":
    unittest.main()
