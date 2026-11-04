import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

from scripts.capture_source import (CaptureError, SafeHTTPSRedirectHandler, capture_url, load_source,
                                     validate_request_url, write_capture)


class FakeResponse:
    def __init__(self, body=b"calendar", url="https://example.org/feed", status=200, headers=None):
        self.body = body
        self.url = url
        self.status = status
        self.headers = Message()
        for key, value in (headers or {"Content-Type": "text/calendar", "ETag": '"abc"'}).items():
            self.headers[key] = value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return self.url

    def read(self, size=-1):
        return self.body[:size]


class CaptureSourceTests(unittest.TestCase):
    def source(self, **overrides):
        row = {
            "id": "sample-feed",
            "source_type": "ics",
            "url": "https://example.org/feed",
            "access_status": "approved",
            "terms_reviewed": True,
            "robots_reviewed": True,
            "polling_enabled": False,
        }
        row.update(overrides)
        return row

    def registry(self, folder, source):
        path = Path(folder) / "sources.json"
        path.write_text(json.dumps({"source_records": [source]}), encoding="utf-8")
        return path

    def test_registry_gate_rejects_unapproved_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(access_status="review_required"))
            with self.assertRaisesRegex(CaptureError, "not approved"):
                load_source(path, "sample-feed")

    def test_registry_gate_rejects_unreviewed_terms(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(terms_reviewed=False))
            with self.assertRaisesRegex(CaptureError, "terms_reviewed=true"):
                load_source(path, "sample-feed")

    def test_registry_gate_rejects_unreviewed_robots(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(robots_reviewed=False))
            with self.assertRaisesRegex(CaptureError, "robots_reviewed=true"):
                load_source(path, "sample-feed")

    def test_written_consent_is_additional_to_all_standard_gates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(
                consent_required=True, consent_granted=True,
            ))
            source = load_source(path, "sample-feed")
            self.assertTrue(source["consent_granted"])
            self.assertFalse(source["polling_enabled"])

    def test_consent_does_not_override_access_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(
                access_status="blocked", consent_required=True, consent_granted=True,
            ))
            with self.assertRaisesRegex(CaptureError, "not approved"):
                load_source(path, "sample-feed")

    def test_consent_does_not_override_terms_review(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(
                consent_required=True, consent_granted=True, terms_reviewed=False,
            ))
            with self.assertRaisesRegex(CaptureError, "terms_reviewed=true"):
                load_source(path, "sample-feed")

    def test_consent_does_not_override_robots_review(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(
                consent_required=True, consent_granted=True, robots_reviewed=False,
            ))
            with self.assertRaisesRegex(CaptureError, "robots_reviewed=true"):
                load_source(path, "sample-feed")

    def test_consent_required_source_is_blocked_until_flag_is_true(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(
                consent_required=True, consent_granted=False,
            ))
            with self.assertRaisesRegex(CaptureError, "consent_granted=true"):
                load_source(path, "sample-feed")

    def test_non_https_and_credential_urls_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(url="http://example.org/feed"))
            with self.assertRaisesRegex(CaptureError, "HTTPS"):
                load_source(path, "sample-feed")
            path = self.registry(folder, self.source(url="https://user:pass@example.org/feed"))
            with self.assertRaisesRegex(CaptureError, "HTTPS"):
                load_source(path, "sample-feed")

    def test_capture_records_hash_headers_and_raw_bytes(self):
        response = FakeResponse(headers={
            "Content-Type": "text/calendar", "ETag": '"v1"',
            "Last-Modified": "Tue, 03 Nov 2026 12:00:00 GMT",
        })
        body, metadata = capture_url("https://example.org/feed", opener=lambda request, timeout: response)
        self.assertEqual(body, b"calendar")
        self.assertEqual(metadata["content_length"], 8)
        self.assertEqual(metadata["etag"], '"v1"')
        self.assertEqual(len(metadata["content_sha256"]), 64)
        with tempfile.TemporaryDirectory() as folder:
            meta_path = write_capture("sample-feed", body, metadata, Path(folder))
            saved_metadata = json.loads(meta_path.read_text())
            self.assertEqual((meta_path.parent / saved_metadata["raw_payload_file"]).read_bytes(), body)
            self.assertEqual(saved_metadata["outcome"], "captured")

    def test_conditional_headers_are_sent(self):
        response = FakeResponse()
        def opener(request, timeout):
            self.assertEqual(request.get_header("If-none-match"), '"v1"')
            self.assertEqual(request.get_header("If-modified-since"), "yesterday")
            return response
        body, metadata = capture_url(
            "https://example.org/feed", etag='"v1"',
            last_modified="yesterday", opener=opener,
        )
        self.assertEqual(body, b"calendar")
        self.assertEqual(metadata["outcome"], "captured")

    def test_http_304_is_successful_unchanged_capture(self):
        headers = Message()
        headers["ETag"] = '"v1"'
        error = HTTPError("https://example.org/feed", 304, "Not Modified", headers, None)
        with self.assertRaises(HTTPError):
            # Confirm the standard exception shape used by urllib before testing capture handling.
            raise error
        def opener(request, timeout):
            raise error
        body, metadata = capture_url("https://example.org/feed", etag='"v1"', opener=opener)
        self.assertIsNone(body)
        self.assertEqual(metadata["outcome"], "not_modified")
        self.assertEqual(metadata["http_status"], 304)

    def test_insecure_redirect_target_is_rejected(self):
        handler = SafeHTTPSRedirectHandler()
        request = __import__("urllib.request", fromlist=["Request"]).Request("https://example.org/feed")
        with self.assertRaisesRegex(CaptureError, "unsafe URL"):
            handler.redirect_request(request, None, 302, "Found", {}, "http://example.org/redirected")

    def test_archive_rejects_unsafe_source_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(CaptureError, "unsafe for an archive path"):
                write_capture("../outside", b"x", {"captured_at": "2026-11-04T12:00:00+00:00",
                    "content_sha256": "abc"}, Path(folder))

    def test_alternate_page_url_requires_source_allowlist(self):
        source = self.source(
            id="village-of-mokena-events",
            url="https://www.mokena.gov/calendar.aspx",
        )
        with tempfile.TemporaryDirectory() as folder:
            policies = Path(folder) / "policies.json"
            policies.write_text(json.dumps({"profiles": [{
                "source_id": "village-of-mokena-events",
                "allowed_hosts": ["www.mokena.gov", "mokenail.municipalone.com"],
                "allowed_paths": ["/calendar.aspx", "/calendarView.aspx"],
            }]}), encoding="utf-8")
            url = "https://mokenail.municipalone.com/calendarView.aspx?cid=123"
            self.assertEqual(validate_request_url(source, url, policies), url)
            with self.assertRaisesRegex(CaptureError, "allowlist"):
                validate_request_url(source, "https://evil.example/calendarView.aspx?cid=123", policies)
            with self.assertRaisesRegex(CaptureError, "allowlist"):
                validate_request_url(source, "https://www.mokena.gov/private", policies)
            with self.assertRaisesRegex(CaptureError, "HTTPS"):
                validate_request_url(source, "http://mokenail.municipalone.com/calendarView.aspx?cid=123", policies)

    def test_canonical_source_url_needs_no_alternate_allowlist(self):
        source = self.source()
        self.assertEqual(validate_request_url(source, source["url"]), source["url"])

    def test_source_types_outside_http_capture_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(source_type="email"))
            with self.assertRaisesRegex(CaptureError, "not supported"):
                load_source(path, "sample-feed")


if __name__ == "__main__":
    unittest.main()
