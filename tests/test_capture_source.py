import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from scripts.capture_source import CaptureError, capture_url, load_source, write_capture


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

    def test_registry_gate_rejects_unreviewed_terms_or_robots(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(robots_reviewed=False))
            with self.assertRaisesRegex(CaptureError, "terms_reviewed=true"):
                load_source(path, "sample-feed")

    def test_written_consent_switch_is_preserved_without_enabling_polling(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(
                access_status="blocked", consent_required=True, consent_granted=True,
                robots_reviewed=False,
            ))
            source = load_source(path, "sample-feed")
            self.assertTrue(source["consent_granted"])
            self.assertFalse(source["polling_enabled"])

    def test_consent_required_source_is_blocked_until_flag_is_true(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(
                access_status="blocked", consent_required=True, consent_granted=False,
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
        with patch("scripts.capture_source.urlopen", return_value=response):
            body, metadata = capture_url("https://example.org/feed")
        self.assertEqual(body, b"calendar")
        self.assertEqual(metadata["content_length"], 8)
        self.assertEqual(metadata["etag"], '"v1"')
        self.assertEqual(len(metadata["content_sha256"]), 64)
        with tempfile.TemporaryDirectory() as folder:
            meta_path = write_capture("sample-feed", body, metadata, Path(folder))
            self.assertEqual(meta_path.with_suffix(".bin").read_bytes(), body)
            self.assertEqual(json.loads(meta_path.read_text())["outcome"], "captured")

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
        response = FakeResponse(url="http://example.org/redirected")
        with patch("scripts.capture_source.urlopen", return_value=response):
            with self.assertRaisesRegex(CaptureError, "unsafe URL"):
                capture_url("https://example.org/feed")

    def test_source_types_outside_http_capture_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = self.registry(folder, self.source(source_type="email"))
            with self.assertRaisesRegex(CaptureError, "not supported"):
                load_source(path, "sample-feed")


if __name__ == "__main__":
    unittest.main()
