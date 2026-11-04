#!/usr/bin/env python3
"""Run CivicCal's three initial source parsers against local fixtures only.

This is a deterministic integration check. It performs no network requests,
does not read source URLs, and does not publish or persist event records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.parse_ics import parse_ics
from scripts.parse_mokena_park import parse_html as parse_park_html
from scripts.parse_village import parse_html as parse_village_html


ROOT = Path(__file__).resolve().parents[1]


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

    village_url = (
        "https://www.mokena.gov/calendarView.aspx?catid=0&cid=30642&id=0"
    )
    village = parse_village_html(
        _read(root / "data/fixtures/village-calendar-detail.html"),
        page_url=village_url,
    )
    village_events = village["events"]
    assert village["event_count"] == 1, "Village detail fixture should yield one event"
    assert village_events[0]["uid"] == "30642"
    assert village_events[0]["title"] == "Village of Mokena's Food Trucks on Front"
    assert village_events[0]["start_text"] == "Wednesday September 16, 2026"
    assert village_events[0]["time_text"] == "4:00 PM - 8:00 PM"
    assert village_events[0]["timezone"] is None
    assert village_events[0]["description"] is None

    sources = [
        {
            "source_id": ics["source_id"],
            "parser": "parse_ics",
            "fixture": "data/fixtures/sample-community.ics",
            "event_count": ics["event_count"],
            "warning_count": len(ics["warnings"]),
            "warnings": ics["warnings"],
            "checks": [
                "UID retained",
                "America/Chicago TZID retained",
                "CANCELLED status retained",
            ],
        },
        {
            "source_id": park["source_id"],
            "parser": "parse_mokena_park",
            "fixture": "data/fixtures/mokena-park-upcoming.html",
            "event_count": park["event_count"],
            "warning_count": len(park["warnings"]),
            "warnings": park["warnings"],
            "checks": [
                "event cards extracted",
                "registration deadline kept separate",
                "judging date not promoted to event date",
                "explicit year retained",
            ],
        },
        {
            "source_id": village["source_id"],
            "parser": "parse_village",
            "fixture": "data/fixtures/village-calendar-detail.html",
            "event_count": village["event_count"],
            "warning_count": len(village["warnings"]),
            "warnings": village["warnings"],
            "checks": [
                "event identifier retained",
                "title/date/time extracted",
                "timezone not guessed",
                "empty Details field remains empty",
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
        f"{report['event_count']} events; "
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
