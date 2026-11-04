#!/usr/bin/env python3
"""Run one manually initiated, source-scoped Village calendar capture.

The coordinator follows only parser-discovered rel=next and calendarView detail
links that pass the source's explicit host/path allowlist. It never schedules,
publishes, or enables polling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import build_opener

from scripts.capture_source import (
    CaptureError,
    SafeHTTPSRedirectHandler,
    capture_url,
    load_source,
    validate_request_url,
    write_capture,
)
from scripts.normalize_events import normalize_event
from scripts.parse_village import parse_html as parse_village
from scripts.validate_snapshot import validate_manifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "sources.json"
DEFAULT_POLICIES = ROOT / "data" / "source-completeness.json"
DEFAULT_ARCHIVE = ROOT / "data" / "captures"
VILLAGE_SOURCE_ID = "village-of-mokena-events"


class CoordinationError(Exception):
    """Expected coordinator input or capture failure."""


class ScopedRedirectHandler(SafeHTTPSRedirectHandler):
    """Check every redirect destination against the source-specific allowlist."""

    def __init__(self, source: dict, policies_path: Path) -> None:
        super().__init__()
        self.source = source
        self.policies_path = policies_path

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_request_url(self.source, newurl, self.policies_path)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _event_id_from_url(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("cid", [])
    return values[0] if len(values) == 1 and values[0].strip() else None


def _page_record(url: str, role: str, outcome: str, status: int | None,
                 parse_status: str, digest: str | None,
                 source_event_ids: list[str] | None = None,
                 discovered_detail_ids: list[str] | None = None) -> dict:
    return {
        "role": role,
        "url": url,
        "capture_outcome": outcome,
        "http_status": status,
        "parse_status": parse_status,
        "content_sha256": digest,
        "source_event_ids": source_event_ids or [],
        "discovered_detail_ids": discovered_detail_ids or [],
    }


def coordinate_village_capture(source: dict, policies_path: Path, archive_dir: Path,
                               *, max_pages: int = 20, max_details: int = 500,
                               timeout: int = 20, opener_factory=None) -> dict:
    """Capture and parse the Village listing, its next pages, and linked details."""
    if source.get("id") != VILLAGE_SOURCE_ID:
        raise CoordinationError("This coordinator currently supports the Village of Mokena source only.")
    if max_pages < 1 or max_details < 1:
        raise CoordinationError("Page and detail limits must both be positive.")
    policies = json.loads(policies_path.read_text(encoding="utf-8"))
    profiles = [p for p in policies.get("profiles", [])
                if p.get("source_id") == source["id"]]
    if len(profiles) != 1:
        raise CoordinationError("Exactly one Village source completeness profile is required.")
    profile = profiles[0]

    first_url = validate_request_url(source, source["url"], policies_path)
    listing_queue = [first_url]
    seen_listing_urls: set[str] = set()
    detail_urls: dict[str, str] = {}
    pages: list[dict] = []
    normalized_events: list[dict] = []
    captured_pages: list[dict] = []
    warnings: list[str] = []
    pending_urls: list[str] = []
    page_limit_hit = False
    detail_limit_hit = False
    pagination_cycle = False

    def capture_page(url: str, role: str) -> tuple[bytes, dict, Path]:
        allowed_url = validate_request_url(source, url, policies_path)
        opener = (opener_factory(source, policies_path) if opener_factory
                  else build_opener(ScopedRedirectHandler(source, policies_path)).open)
        body, metadata = capture_url(allowed_url, timeout=timeout, opener=opener)
        if body is None:
            raise CaptureError("HTTP 304 returned no payload; a fresh page capture is required for this run.")
        metadata.update({
            "format": "civiccal.raw-capture.v1",
            "source_id": source["id"],
            "source_type": source["source_type"],
            "source_url": source["url"],
            "page_role": role,
        })
        metadata_path = write_capture(source["id"], body, metadata, archive_dir)
        return body, metadata, metadata_path

    # Traverse only explicit rel=next links emitted by the existing parser.
    while listing_queue and len(seen_listing_urls) < max_pages:
        url = listing_queue.pop(0)
        if url in seen_listing_urls:
            continue
        seen_listing_urls.add(url)
        try:
            body, metadata, metadata_path = capture_page(url, "listing")
            html = body.decode("utf-8-sig")
            parsed = parse_village(html, page_url=metadata.get("final_url") or url)
            if parsed.get("page_type") != "calendar_listing":
                raise CoordinationError("A listing URL was parsed as a non-listing page.")
            discovered_ids: list[str] = []
            for link in parsed.get("detail_links", []):
                link_url = link.get("url")
                event_id = _event_id_from_url(link_url) if isinstance(link_url, str) else None
                if not event_id:
                    warnings.append(f"Listing link without one unambiguous cid was ignored: {link_url!r}")
                    continue
                validate_request_url(source, link_url, policies_path)
                detail_urls.setdefault(event_id, link_url)
                if event_id not in discovered_ids:
                    discovered_ids.append(event_id)
            pages.append(_page_record(
                metadata.get("final_url") or url, "listing", "captured",
                metadata.get("http_status"), "success", metadata.get("content_sha256"),
                discovered_detail_ids=discovered_ids,
            ))
            captured_pages.append({
                "url": metadata.get("final_url") or url,
                "role": "listing",
                "metadata_file": str(metadata_path),
                "parser_output": parsed,
            })
            for next_url in parsed.get("pagination", {}).get("next_page_urls", []):
                validate_request_url(source, next_url, policies_path)
                if next_url in seen_listing_urls:
                    pagination_cycle = True
                    warnings.append(f"Pagination cycle detected at {next_url}; terminal page is not established.")
                elif next_url not in listing_queue:
                    listing_queue.append(next_url)
        except Exception as exc:
            warnings.append(f"Listing page failed ({url}): {exc}")
            pages.append(_page_record(url, "listing", "failed", None, "failed", None))

    if listing_queue:
        page_limit_hit = True
        pending_urls.extend(listing_queue)
        warnings.append(f"Listing page limit reached ({max_pages}); remaining pages were not fetched.")

    detail_items = list(detail_urls.items())
    for index, (expected_id, url) in enumerate(detail_items):
        if index >= max_details:
            detail_limit_hit = True
            pending_urls.extend(detail_url for _, detail_url in detail_items[index:])
            warnings.append(f"Event-detail limit reached ({max_details}); remaining detail pages were not fetched.")
            break
        try:
            body, metadata, metadata_path = capture_page(url, "detail")
            html = body.decode("utf-8-sig")
            parsed = parse_village(html, page_url=metadata.get("final_url") or url)
            events = parsed.get("events", [])
            actual_ids = [str(event.get("uid")) for event in events if event.get("uid") is not None]
            if expected_id not in actual_ids:
                warnings.append(f"Detail page cid={expected_id} did not return a matching event ID.")
            pages.append(_page_record(
                metadata.get("final_url") or url, "detail", "captured",
                metadata.get("http_status"), "success", metadata.get("content_sha256"),
                source_event_ids=actual_ids,
            ))
            captured_pages.append({
                "url": metadata.get("final_url") or url,
                "role": "detail",
                "metadata_file": str(metadata_path),
                "parser_output": parsed,
            })
            capture_ref = {
                "captured_at": metadata.get("captured_at"),
                "content_sha256": metadata.get("content_sha256"),
                "final_url": metadata.get("final_url"),
                "metadata_file": str(metadata_path),
                "http_status": metadata.get("http_status"),
                "outcome": metadata.get("outcome"),
                "page_role": "detail",
            }
            for event in events:
                normalized_events.append(normalize_event(event, source["id"], capture_ref))
        except Exception as exc:
            warnings.append(f"Detail page failed (cid={expected_id}, {url}): {exc}")
            pages.append(_page_record(url, "detail", "failed", None, "failed", None))

    manifest = {
        "format": "civiccal.snapshot-manifest.v1",
        "source_id": source["id"],
        "pagination": {
            "strategy": profile.get("pagination_strategy"),
            "expected_page_count": len(pages),
            "observed_page_count": len(pages),
            "terminal_page_confirmed": not listing_queue and not page_limit_hit and not pagination_cycle,
            "pending_next_urls": pending_urls,
        },
        "pages": pages,
    }
    snapshot = validate_manifest(manifest, profile)
    if detail_limit_hit:
        snapshot["completeness"] = "partial"
        snapshot["blockers"].append("One or more discovered event-detail pages were not processed.")
    if pagination_cycle:
        snapshot["completeness"] = "partial"
        snapshot["blockers"].append("Pagination links formed a cycle; a terminal page was not established.")
    if warnings and snapshot["completeness"] == "complete":
        snapshot["completeness"] = "partial"
        snapshot["blockers"].extend(warnings)

    normalized = {
        "format": "civiccal.normalized-events.v1",
        "source_id": source["id"],
        "capture": {
            "method": "manual-source-scoped-coordinator",
            "source_url": source["url"],
            "page_count": len(pages),
        },
        "parser_format": "civiccal.village-events.v1",
        "source_event_count": len(normalized_events),
        "event_count": len(normalized_events),
        "events": normalized_events,
        "parser_warnings": warnings,
        "snapshot": snapshot,
        "coordinator": {
            "format": "civiccal.coordinated-capture.v1",
            "captured_pages": captured_pages,
            "manifest": manifest,
            "limits": {"max_pages": max_pages, "max_details": max_details},
            "automatic_polling_enabled": False,
            "published": False,
        },
        "summary": {
            "events_with_review_flags": sum(bool(event["data_quality_flags"]) for event in normalized_events),
            "listing_pages": sum(page["role"] == "listing" for page in pages),
            "detail_pages": sum(page["role"] == "detail" for page in pages),
        },
    }
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-details", type=int, default=500)
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()
    try:
        source = load_source(args.registry, args.source_id)
        result = coordinate_village_capture(
            source, args.policies, args.archive_dir,
            max_pages=args.max_pages, max_details=args.max_details,
            timeout=args.timeout,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Captured {result['summary']['listing_pages']} listing page(s) and "
              f"{result['summary']['detail_pages']} detail page(s).")
        print(f"Normalized events: {result['event_count']}")
        print(f"Snapshot completeness: {result['snapshot']['completeness']}")
        for blocker in result["snapshot"]["blockers"]:
            print(f"- {blocker}")
        print(f"Output: {args.output}")
        return 0
    except (CaptureError, CoordinationError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
