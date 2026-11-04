#!/usr/bin/env python3
"""Run one manually initiated capture of a registered iCalendar source.

This coordinator captures exactly one ICS feed, archives the original bytes,
parses and normalizes VEVENT records, and validates a single-feed manifest.
It never schedules, publishes, or enables polling.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.request import build_opener

from scripts.capture_source import (
    CaptureError,
    SafeHTTPSRedirectHandler,
    capture_url,
    load_source,
    validate_request_url,
    write_capture,
)
from scripts.normalize_events import NormalizationError, normalize_document
from scripts.parse_ics import parse_ics
from scripts.validate_snapshot import SnapshotError, validate_manifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "sources.json"
DEFAULT_POLICIES = ROOT / "data" / "source-completeness.json"
DEFAULT_ARCHIVE = ROOT / "data" / "captures"


class ICSCoordinatorError(Exception):
    """Expected source, capture, or feed validation failure."""


class ScopedRedirectHandler(SafeHTTPSRedirectHandler):
    """Require redirect targets to remain inside the registered source allowlist."""

    def __init__(self, source: dict, policies_path: Path) -> None:
        super().__init__()
        self.source = source
        self.policies_path = policies_path

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_request_url(self.source, newurl, self.policies_path)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def coordinate_ics_capture(source: dict, policies_path: Path, archive_dir: Path,
                           *, timeout: int = 20, opener_factory=None,
                           empty_snapshot_confirmed: bool = False) -> dict:
    """Capture and normalize one registered ICS feed without changing source state."""
    if source.get("source_type") != "ics":
        raise ICSCoordinatorError("The iCalendar coordinator accepts only registered ICS sources.")
    source_id = source.get("id")
    if not isinstance(source_id, str) or not source_id:
        raise ICSCoordinatorError("The source has no valid registry ID.")

    try:
        policies = json.loads(policies_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ICSCoordinatorError(f"Cannot read source completeness policies: {exc}") from exc
    profiles = [p for p in policies.get("profiles", [])
                if isinstance(p, dict) and p.get("source_id") == source_id]
    if len(profiles) != 1:
        raise ICSCoordinatorError("Exactly one source-specific completeness profile is required.")
    profile = profiles[0]
    if profile.get("pagination_strategy") != "single_feed":
        raise ICSCoordinatorError("This ICS coordinator requires a single_feed completeness policy.")

    request_url = validate_request_url(source, source.get("url", ""), policies_path)
    opener = (opener_factory(source, policies_path) if opener_factory
              else build_opener(ScopedRedirectHandler(source, policies_path)).open)
    body, metadata = capture_url(request_url, timeout=timeout, opener=opener)
    metadata.update({
        "format": "civiccal.raw-capture.v1",
        "source_id": source_id,
        "source_type": "ics",
        "source_url": source["url"],
        "page_role": "feed",
    })
    metadata_path = write_capture(source_id, body, metadata, archive_dir)

    if body is None:
        raise ICSCoordinatorError(
            "The feed returned HTTP 304 (not modified). No new payload was parsed; "
            "reuse the previous archived capture and parse result instead."
        )
    final_url = metadata.get("final_url") or request_url
    validate_request_url(source, final_url, policies_path)
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ICSCoordinatorError("The captured iCalendar feed is not valid UTF-8.") from exc

    upper = text.upper()
    if "BEGIN:VCALENDAR" not in upper or "END:VCALENDAR" not in upper:
        raise ICSCoordinatorError("The response does not contain a complete VCALENDAR envelope.")

    parsed = parse_ics(text, source_id=source_id, source_url=final_url)
    capture_ref = {
        "metadata_file": str(metadata_path),
        "captured_at": metadata.get("captured_at"),
        "content_sha256": metadata.get("content_sha256"),
        "final_url": final_url,
        "requested_url": metadata.get("requested_url"),
        "source_url": source["url"],
        "http_status": metadata.get("http_status"),
        "outcome": metadata.get("outcome"),
        "page_role": "feed",
    }
    parse_envelope = {
        "format": "civiccal.parse-result.v1",
        "source_id": source_id,
        "adapter": "ics",
        "capture": capture_ref,
        "parser_output": parsed,
    }
    try:
        normalized = normalize_document(parse_envelope)
    except NormalizationError as exc:
        raise ICSCoordinatorError(f"Could not normalize the captured feed: {exc}") from exc

    publisher_ids = [
        str(event["source_event_id"])
        for event in normalized["events"]
        if event.get("source_event_id") is not None and str(event["source_event_id"]).strip()
    ]
    manifest = {
        "format": "civiccal.snapshot-manifest.v1",
        "source_id": source_id,
        "pagination": {
            "strategy": "single_feed",
            "expected_page_count": 1,
            "observed_page_count": 1,
            "terminal_page_confirmed": True,
            "pending_next_urls": [],
        },
        "pages": [{
            "role": "feed",
            "url": final_url,
            "capture_outcome": metadata.get("outcome"),
            "http_status": metadata.get("http_status"),
            "parse_status": "success" if not parsed.get("warnings") else "partial",
            "content_sha256": metadata.get("content_sha256"),
            "source_event_ids": sorted(set(publisher_ids)),
            "discovered_detail_ids": [],
        }],
    }
    if empty_snapshot_confirmed:
        manifest["empty_snapshot_confirmed"] = True
    try:
        snapshot = validate_manifest(manifest, profile)
    except SnapshotError as exc:
        raise ICSCoordinatorError(f"Could not validate the single-feed manifest: {exc}") from exc
    normalized["snapshot"] = snapshot
    normalized["coordinator"] = {
        "format": "civiccal.coordinated-capture.v1",
        "method": "manual-single-ics-feed",
        "manifest": manifest,
        "raw_capture_metadata": str(metadata_path),
        "automatic_polling_enabled": False,
        "published": False,
    }
    normalized["summary"]["parser_warning_count"] = len(parsed.get("warnings", []))
    normalized["summary"]["publisher_id_count"] = len(set(publisher_ids))
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--confirm-empty-snapshot", action="store_true",
                        help="Explicitly attest that a valid feed intentionally contains no VEVENTs.")
    args = parser.parse_args()
    try:
        if not 1 <= args.timeout <= 120:
            raise ICSCoordinatorError("--timeout must be between 1 and 120 seconds.")
        source = load_source(args.registry, args.source_id)
        result = coordinate_ics_capture(
            source, args.policies, args.archive_dir,
            timeout=args.timeout,
            empty_snapshot_confirmed=args.confirm_empty_snapshot,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Captured and normalized {result['event_count']} event(s) from {args.source_id}.")
        print(f"Snapshot completeness: {result['snapshot']['completeness']}")
        for blocker in result["snapshot"]["blockers"]:
            print(f"- {blocker}")
        print(f"Output: {args.output}")
        return 0
    except (CaptureError, ICSCoordinatorError, NormalizationError, SnapshotError,
            OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
