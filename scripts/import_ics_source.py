#!/usr/bin/env python3
"""Manually fetch one approved CivicCal ICS source and report changes.

This command is intentionally one-shot. It does not schedule itself, update the
source registry, publish events, or treat missing events as cancellations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

try:  # Support both direct script execution and package-based tests.
    from .parse_ics import parse_ics
except ImportError:  # pragma: no cover - exercised by the CLI entry point
    from parse_ics import parse_ics

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "sources.json"
USER_AGENT = "CivicCal/0.1 (+https://github.com/thebakermark/CivicCal)"
MAX_BYTES = 20 * 1024 * 1024


class ImportErrorSafe(Exception):
    """Expected validation or fetch error suitable for a concise CLI message."""


def load_source(registry_path: Path, source_id: str) -> dict:
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ImportErrorSafe(f"Cannot read source registry: {exc}") from exc
    matches = [row for row in registry.get("source_records", []) if row.get("id") == source_id]
    if len(matches) != 1:
        raise ImportErrorSafe(f"Expected exactly one registry source named {source_id!r}; found {len(matches)}.")
    source = matches[0]
    if source.get("source_type") != "ics":
        raise ImportErrorSafe(f"Source {source_id!r} is not an ICS source.")
    if source.get("access_status") != "approved":
        raise ImportErrorSafe(f"Source {source_id!r} is not approved; current status is {source.get('access_status')!r}.")
    if source.get("terms_reviewed") is not True or source.get("robots_reviewed") is not True:
        raise ImportErrorSafe("Source must have terms_reviewed=true and robots_reviewed=true before fetching.")
    parsed = urlparse(source.get("url", ""))
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ImportErrorSafe("ICS source URL must be a credential-free HTTPS URL.")
    return source


def fetch_ics(url: str, timeout: int = 20) -> tuple[bytes, dict]:
    request = Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/calendar, text/plain;q=0.9, */*;q=0.1",
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            final = urlparse(final_url)
            if final.scheme != "https" or not final.netloc:
                raise ImportErrorSafe("Source redirected to a non-HTTPS URL; refusing the response.")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise ImportErrorSafe(f"Calendar exceeds the {MAX_BYTES // (1024 * 1024)} MiB safety limit.")
            content_type = response.headers.get("Content-Type", "")
            if "text/calendar" not in content_type.lower() and not body.lstrip().startswith(b"BEGIN:VCALENDAR"):
                raise ImportErrorSafe(f"Response does not look like an ICS calendar (Content-Type: {content_type or 'missing'}).")
            metadata = {
                "final_url": final_url,
                "content_type": content_type,
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
                "http_status": getattr(response, "status", 200),
            }
            return body, metadata
    except HTTPError as exc:
        raise ImportErrorSafe(f"Calendar server returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise ImportErrorSafe(f"Could not fetch calendar: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ImportErrorSafe("Calendar request timed out.") from exc


def event_map(document: dict) -> dict[str, dict]:
    result = {}
    for event in document.get("events", []):
        uid = event.get("uid")
        if not uid:
            continue
        if uid in result:
            raise ImportErrorSafe(f"Feed contains repeated UID {uid!r}; refusing ambiguous UID comparison.")
        result[uid] = event
    return result


def comparable(event: dict) -> dict:
    # Source identifiers and URLs are provenance, not event-content changes.
    ignored = {"source_id", "source_url"}
    return {key: value for key, value in event.items() if key not in ignored}


def compare_snapshots(previous: dict | None, current: dict) -> dict:
    now = event_map(current["calendar"])
    if previous is None:
        return {
            "comparison": "baseline",
            "added": sorted(now),
            "changed": [],
            "missing": [],
            "note": "First snapshot: all observed UIDs are baseline records, not newly announced events.",
        }
    before = event_map(previous.get("calendar", {}))
    added = sorted(set(now) - set(before))
    missing = sorted(set(before) - set(now))
    changed = sorted(uid for uid in set(now) & set(before) if comparable(now[uid]) != comparable(before[uid]))
    return {
        "comparison": "compared",
        "added": added,
        "changed": [{"uid": uid, "before": before[uid], "after": now[uid]} for uid in changed],
        "missing": missing,
        "note": "Missing means absent from this successful fetch; it is not a cancellation. Review before changing event status.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True, help="ICS source ID from data/sources.json")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--previous-snapshot", type=Path, help="Prior snapshot JSON for change comparison")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for snapshot.json and change-report.json")
    parser.add_argument("--timeout", type=int, default=20)
    args = parser.parse_args()

    try:
        if not 1 <= args.timeout <= 120:
            raise ImportErrorSafe("--timeout must be between 1 and 120 seconds.")
        source = load_source(args.registry, args.source_id)
        previous = None
        if args.previous_snapshot:
            try:
                previous = json.loads(args.previous_snapshot.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ImportErrorSafe(f"Cannot read previous snapshot: {exc}") from exc

        body, response = fetch_ics(source["url"], args.timeout)
        calendar = parse_ics(body.decode("utf-8-sig"), source_id=source["id"], source_url=source["url"])
        if calendar["warnings"]:
            print(f"WARNING: parser reported {len(calendar['warnings'])} warning(s); inspect snapshot.json.", file=sys.stderr)
        if any(not event.get("uid") for event in calendar["events"]):
            raise ImportErrorSafe("At least one event has no UID; refusing to produce a UID-based change report.")

        snapshot = {
            "format": "civiccal.source-snapshot.v1",
            "source_id": source["id"],
            "source_url": source["url"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "content_sha256": hashlib.sha256(body).hexdigest(),
            "response": response,
            "calendar": calendar,
        }
        report = {
            "format": "civiccal.change-report.v1",
            "source_id": source["id"],
            "fetched_at": snapshot["fetched_at"],
            "event_count": calendar["event_count"],
            "parser_warning_count": len(calendar["warnings"]),
            "content_sha256": snapshot["content_sha256"],
            **compare_snapshots(previous, snapshot),
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "snapshot.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (args.output_dir / "change-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Fetched {calendar['event_count']} events from {source['id']}.")
        print(f"Comparison: {report['comparison']}; added={len(report['added'])}; changed={len(report['changed'])}; missing={len(report['missing'])}.")
        print(f"Output: {args.output_dir / 'snapshot.json'} and {args.output_dir / 'change-report.json'}")
        return 0
    except ImportErrorSafe as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
