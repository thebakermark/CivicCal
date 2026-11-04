#!/usr/bin/env python3
"""Build an offline .ics preview from the saved, verified Village event fixture.

This is a local fixture demonstration only: no network access, source capture,
production state changes, or live publication occurs. The fixture event is
explicitly approved inside this temporary preview build so the feed renderer
can be exercised end to end.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.parse_village import parse_html
from scripts.normalize_events import normalize_document
from scripts.track_event_identity import process_normalized
from scripts.publish_ics import build_calendar


SOURCE_ID = "village-of-mokena-events"
EVENT_URL = (
    "https://www.mokena.gov/calendarView.aspx"
    "?catid=0&cid=28236&id=0"
)


def build_preview() -> str:
    html = (ROOT / "data/fixtures/village-calendar-detail.html").read_text(
        encoding="utf-8"
    )
    parsed = parse_html(html, page_url=EVENT_URL)
    parsed["source_id"] = SOURCE_ID
    for event in parsed["events"]:
        event["source_id"] = SOURCE_ID
        event["source_url"] = EVENT_URL

    normalized = normalize_document(parsed)
    if normalized.get("event_count") != 1:
        raise ValueError("Expected exactly one Village event in the saved fixture.")

    result, state = process_normalized(
        normalized,
        prior_state=None,
        observed_at="2026-11-04T12:00:00Z",
    )
    if result.get("new_events") != 1:
        raise ValueError("Fixture did not produce exactly one tracked event.")

    event_records = list(state["events"].values())
    if len(event_records) != 1:
        raise ValueError("Expected exactly one tracked event record.")
    event_id = event_records[0]["event_id"]

    # This approval exists only in this temporary fixture preview. It does not
    # modify data/publication.json or change the registered source's review gates.
    manifest = {
        "format": "civiccal.publication-manifest.v1",
        "calendar_name": "Village of Mokena Events (offline fixture preview)",
        "approved_event_ids": [event_id],
    }
    rendered, summary = build_calendar(state, manifest)
    if summary.get("published_count") != 1:
        raise ValueError("Expected one event in the generated fixture feed.")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    rendered = build_preview()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(rendered.encode("utf-8"))
    print(f"Wrote one-event offline fixture feed: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
