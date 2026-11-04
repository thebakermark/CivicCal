#!/usr/bin/env python3
"""Run CivicCal's three initial source parsers against local fixtures only.

This is a deterministic integration check. It performs no network requests,
does not read source URLs, and does not publish or persist event records.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Direct script execution puts scripts/ rather than the repository root on
# sys.path. Add the root so the existing scripts namespace imports resolve.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.parse_ics import parse_ics
from scripts.parse_mokena_park import parse_html as parse_park_html
from scripts.parse_village import parse_html as parse_village_html
from scripts.normalize_events import normalize_document


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def validate_fixtures(root: Path = ROOT) -> dict[str, Any]:
    """Parse each checked-in fixture and enforce cross-source expectations."""
    ics = parse_ics(
        _read(root / "data/fixtures/sample-community.ics"),
        source_id="mokena-school-district-159-fixture",
    )
    ics_events = ics["events"]
    assert ics["event_count"] == 2, "ICS fixture should contain two VEVENT records"
    assert ics_events[0]["uid"] == "sample-001@example.org"
    assert ics_events[0]["start"]["timezone"] == "America/Chicago"
    assert ics_events[1]["cancelled"] is True

    park = parse_park_html(_read(root / "data/fixtures/mokena-park-upcoming.html"))
    park_events = park["events"]
    assert park["event_count"] == 3, "Park District fixture should contain three event cards"
    assert park_events[0]["title"] == "Puzzlemania"
    assert park_events[0]["registration_deadline_text"] == ["Registration deadline: November 1."]
    assert park_events[1]["date_text"] is None, "Judging date must not become an event date"
    assert park_events[2]["event_date_year_known"] is True

    village_url = "https://www.mokena.gov/calendarView.aspx?catid=0&cid=28236&id=0"
    village = parse_village_html(
        _read(root / "data/fixtures/village-calendar-detail.html"),
        page_url=village_url,
    )
    village_events = village["events"]
    assert village["event_count"] == 1, "Village detail fixture should yield one event"
    assert village_events[0]["uid"] == "28236"
    assert village_events[0]["title"] == "Chamber of Commerce Parade of Lights & Village Tree Lighting Ceremony"
    assert village_events[0]["start_text"] == "Saturday November 21, 2026"
    assert village_events[0]["time_text"] == "5:00 PM"
    assert village_events[0]["timezone"] is None
    assert village_events[0]["description"].startswith("The Mokena Chamber of Commerce presents the Parade of Lights")

    normalized_sources = [
        normalize_document(ics),
        normalize_document(park),
        normalize_document(village),
    ]
    normalized_by_id = {item["source_id"]: item for item in normalized_sources}

    # Cross-source contract checks: normalization preserves event counts,
    # source provenance, and important date/time semantics.
    normalized_ics = normalized_by_id[ics["source_id"]]
    assert normalized_ics["event_count"] == 2
    assert normalized_ics["events"][0]["start"]["timezone"] == "America/Chicago"
    assert normalized_ics["events"][1]["status"] == "cancelled"

    normalized_park = normalized_by_id[park["source_id"]]
    assert normalized_park["event_count"] == 3
    assert normalized_park["events"][0]["registration_deadline"] == park_events[0]["registration_deadline_text"]
    assert normalized_park["events"][1]["start"] is None

    normalized_village = normalized_by_id[village["source_id"]]
    assert normalized_village["event_count"] == 1
    assert normalized_village["events"][0]["start"]["value"] == "2026-11-21T17:00"
    assert normalized_village["events"][0]["end"] is None
    assert normalized_village["events"][0]["time_status"] == "floating"

    sources = [
        {
            "source_id": ics["source_id"],
            "parser": "parse_ics",
            "fixture": "data/fixtures/sample-community.ics",
            "event_count": ics["event_count"],
            "warning_count": len(ics["warnings"]),
            "warnings": ics["warnings"],
            "normalized_event_count": normalized_ics["event_count"],
            "review_flagged_count": normalized_ics["summary"]["events_with_review_flags"],
            "checks": [
                "UID retained",
                "America/Chicago TZID retained",
                "CANCELLED status retained",
                "canonical event record created",
            ],
        },
        {
            "source_id": park["source_id"],
            "parser": "parse_mokena_park",
            "fixture": "data/fixtures/mokena-park-upcoming.html",
            "event_count": park["event_count"],
            "warning_count": len(park["warnings"]),
            "warnings": park["warnings"],
            "normalized_event_count": normalized_park["event_count"],
            "review_flagged_count": normalized_park["summary"]["events_with_review_flags"],
            "checks": [
                "event cards extracted",
                "registration deadline kept separate",
                "judging date not promoted to event date",
                "explicit year retained",
                "canonical records created without dropping undated cards",
            ],
        },
        {
            "source_id": village["source_id"],
            "parser": "parse_village",
            "fixture": "data/fixtures/village-calendar-detail.html",
            "event_count": village["event_count"],
            "warning_count": len(village["warnings"]),
            "warnings": village["warnings"],
            "normalized_event_count": normalized_village["event_count"],
            "review_flagged_count": normalized_village["summary"]["events_with_review_flags"],
            "checks": [
                "event identifier retained",
                "title/date/time extracted",
                "explicit date and time normalized as floating local time",
                "timezone not guessed",
                "published description retained",
                "canonical event record created",
            ],
        },
    ]

    return {
        "format": "civiccal.fixture-validation.v1",
        "mode": "offline_fixture_only",
        "network_access": False,
        "database_writes": False,
        "publication": False,
        "source_count": len(sources),
        "event_count": sum(source["event_count"] for source in sources),
        "normalized_event_count": sum(source["normalized_event_count"] for source in sources),
        "review_flagged_event_count": sum(source["review_flagged_count"] for source in sources),
        "warning_count": sum(source["warning_count"] for source in sources),
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the full machine-readable report")
    args = parser.parse_args()

    try:
        report = validate_fixtures()
    except (AssertionError, OSError, ValueError, KeyError) as exc:
        print(f"FIXTURE VALIDATION FAILED: {exc}")
        return 1

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print(
        f"Validated {report['source_count']} source fixtures; "
        f"{report['event_count']} parsed events; "
        f"{report['normalized_event_count']} normalized events; "
        f"{report['review_flagged_event_count']} flagged for review; "
        f"{report['warning_count']} parser warnings."
    )
    for source in report["sources"]:
        print(
            f"- {source['source_id']}: {source['event_count']} events "
            f"({source['parser']})"
        )
        for check in source["checks"]:
            print(f"    PASS: {check}")
        for warning in source["warnings"]:
            print(f"    NOTE: {warning}")
    print("Offline only: no network access, database writes, or publication.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
