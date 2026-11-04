#!/usr/bin/env python3
"""Capture one eligible CivicCal source into a content-addressed raw archive.

This is a one-shot capture utility. It never parses events, changes the source
registry, enables polling, or publishes data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "sources.json"
DEFAULT_ARCHIVE = ROOT / "data" / "captures"
USER_AGENT = "CivicCal/0.1 (+https://github.com/thebakermark/CivicCal)"
MAX_BYTES = 20 * 1024 * 1024


class CaptureError(Exception):
    """Expected eligibility, validation, or retrieval error."""


def load_source(registry_path: Path, source_id: str) -> dict:
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError(f"Cannot read source registry: {exc}") from exc

    matches = [row for row in registry.get("source_records", []) if row.get("id") == source_id]
    if len(matches) != 1:
        raise CaptureError(f"Expected exactly one source named {source_id!r}; found {len(matches)}.")
    source = matches[0]

    if source.get("source_type") not in {"ics", "rss", "atom", "json_api", "html"}:
        raise CaptureError(f"Source type {source.get('source_type')!r} is not supported for HTTP capture.")

    # Preserve the explicit written-consent switch used by the SD 159 source.
    if source.get("consent_required") is True:
        if source.get("consent_granted") is not True:
            raise CaptureError(
                f"Source {source_id!r} requires written consent; set consent_granted=true "
                "only after written consent is received."
            )
    else:
        if source.get("access_status") != "approved":
            raise CaptureError(
                f"Source {source_id!r} is not approved; current status is {source.get('access_status')!r}."
            )
        if source.get("terms_reviewed") is not True or source.get("robots_reviewed") is not True:
            raise CaptureError("Source must have terms_reviewed=true and robots_reviewed=true before network capture.")

    parsed = urlparse(source.get("url", ""))
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise CaptureError("Source URL must be a credential-free HTTPS URL.")
    return source


def _validate_https_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise CaptureError("Source redirected to an unsafe URL; only credential-free HTTPS is allowed.")


class SafeHTTPSRedirectHandler(HTTPRedirectHandler):
    """Reject unsafe redirect destinations before making the redirected request."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def capture_url(url: str, *, etag: str | None = None, last_modified: str | None = None,
                timeout: int = 20, opener=None) -> tuple[bytes | None, dict]:
    _validate_https_url(url)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/calendar, application/ics, application/atom+xml, application/rss+xml, "
                  "application/json, text/html, application/xml, text/xml, */*;q=0.1",
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    request = Request(url, headers=headers)
    safe_open = opener or build_opener(SafeHTTPSRedirectHandler()).open
    try:
        with safe_open(request, timeout=timeout) as response:
            final_url = response.geturl()
            _validate_https_url(final_url)
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise CaptureError(f"Response exceeds the {MAX_BYTES // (1024 * 1024)} MiB safety limit.")
            metadata = {
                "requested_url": url,
                "final_url": final_url,
                "http_status": getattr(response, "status", 200),
                "content_type": response.headers.get("Content-Type"),
                "content_length": len(body),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "content_sha256": hashlib.sha256(body).hexdigest(),
                "outcome": "captured",
            }
            return body, metadata
    except HTTPError as exc:
        if exc.code == 304:
            return None, {
                "requested_url": url,
                "final_url": exc.geturl() or url,
                "http_status": 304,
                "content_type": exc.headers.get("Content-Type") if exc.headers else None,
                "content_length": 0,
                "etag": exc.headers.get("ETag") if exc.headers else etag,
                "last_modified": exc.headers.get("Last-Modified") if exc.headers else last_modified,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "content_sha256": None,
                "outcome": "not_modified",
            }
        raise CaptureError(f"Source server returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise CaptureError(f"Could not retrieve source: {exc.reason}") from exc
    except TimeoutError as exc:
        raise CaptureError("Source request timed out.") from exc


def write_capture(source_id: str, body: bytes | None, metadata: dict, archive_dir: Path) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", source_id):
        raise CaptureError("Source ID contains characters that are unsafe for an archive path.")
    target_dir = archive_dir / source_id
    target_dir.mkdir(parents=True, exist_ok=True)
    digest = metadata.get("content_sha256")
    timestamp = re.sub(r"[^0-9TZ]", "", metadata["captured_at"])
    if body is not None and digest:
        payload_path = target_dir / f"{digest}.bin"
        if not payload_path.exists():
            payload_path.write_bytes(body)
        metadata["raw_payload_file"] = payload_path.name
        metadata_stem = f"capture-{timestamp}-{digest[:12]}"
    else:
        metadata["raw_payload_file"] = None
        metadata_stem = f"not-modified-{timestamp}"
    metadata_path = target_dir / f"{metadata_stem}.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    return metadata_path

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--previous-metadata", type=Path,
                        help="Prior capture metadata; its ETag and Last-Modified are sent conditionally.")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    try:
        if not 1 <= args.timeout <= 120:
            raise CaptureError("--timeout must be between 1 and 120 seconds.")
        source = load_source(args.registry, args.source_id)
        previous = {}
        if args.previous_metadata:
            try:
                previous = json.loads(args.previous_metadata.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CaptureError(f"Cannot read previous capture metadata: {exc}") from exc
        body, metadata = capture_url(
            source["url"], etag=previous.get("etag"),
            last_modified=previous.get("last_modified"), timeout=args.timeout,
        )
        metadata.update({
            "format": "civiccal.raw-capture.v1",
            "source_id": source["id"],
            "source_type": source["source_type"],
        })
        path = write_capture(source["id"], body, metadata, args.archive_dir)
        if body is None:
            print(f"Unchanged: {source['id']} (HTTP 304). Metadata: {path}")
        else:
            print(f"Captured {len(body)} bytes from {source['id']}. SHA-256: {metadata['content_sha256']}")
            print(f"Raw payload: {path.with_suffix('.bin')}")
            print(f"Metadata: {path}")
        return 0
    except CaptureError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
