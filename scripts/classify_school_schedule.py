#!/usr/bin/env python3
"""Conservatively classify school calendar events that affect student schedules.

This is deterministic metadata enrichment. It does not invent dates, change
source text, or decide whether a school is open when the publisher is unclear.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

RULES = (
    ("e_learning", re.compile(r"\b(e[- ]learning|remote learning|virtual learning day)\b", re.I),
     "remote_learning", "Explicit e-learning/remote-learning wording"),
    ("school_break", re.compile(r"\b(thanksgiving (?:break|holiday)|(?:winter|spring|summer|fall|holiday) break)\b", re.I),
     "no_school", "Named school break"),
    ("no_school", re.compile(
        r"\b(no school|no student attendance|students? (?:do not|will not) attend|"
        r"school (?:is )?closed|schools? closed|school not in session|"
        r"non[- ]attendance day)\b", re.I),
     "no_school", "Explicit no-school or closure wording"),
    ("early_dismissal", re.compile(r"\b(early dismissal|early release|early out|early student dismissal)\b", re.I),
     "shortened_day", "Explicit early dismissal/release wording"),
    ("half_day", re.compile(r"\b(half[- ]day|1/2 day|½ day)\b", re.I),
     "shortened_day", "Explicit half-day wording"),
    ("late_start", re.compile(r"\b(late start|delayed start|late arrival)\b", re.I),
     "delayed_start", "Explicit delayed-start wording"),
    ("teacher_institute", re.compile(
        r"\b(teacher institute|institute day|teacher in[- ]service|"
        r"professional development|staff development|teacher workday|"
        r"teacher work day)\b", re.I),
     "confirm_student_attendance", "Staff training/workday wording; the source does not explicitly state whether students attend"),
)

FORMAT = "civiccal.school-schedule.v1"


def classify_event(event: dict[str, Any]) -> dict[str, Any]:
    title = event.get("title") if isinstance(event.get("title"), str) else ""
    description = event.get("description") if isinstance(event.get("description"), str) else ""
    categories = event.get("categories")
    category_text = " ".join(str(x) for x in categories) if isinstance(categories, list) else ""
    haystack = " | ".join(x for x in (title, description, category_text) if x)

    for schedule_type, pattern, attendance, rationale in RULES:
        if pattern.search(haystack):
            return {
                "is_schedule_exception": True,
                "schedule_type": schedule_type,
                "student_attendance": attendance,
                "classification": "rule_based",
                "matched_rule": schedule_type,
                "rationale": rationale,
            }

    return {
        "is_schedule_exception": False,
        "schedule_type": "unclassified",
        "student_attendance": "unknown",
        "classification": "not_matched",
        "matched_rule": None,
        "rationale": None,
    }


def _school_source_ids(registry: dict[str, Any]) -> set[str]:
    organizations = {
        item.get("id"): item
        for item in registry.get("organizations", [])
        if isinstance(item, dict)
    }
    return {
        source.get("id")
        for source in registry.get("source_records", [])
        if isinstance(source, dict)
        and organizations.get(source.get("organization_id"), {}).get("type") == "school"
        and isinstance(source.get("id"), str)
    }


def classify_document(document: dict[str, Any], school_source_ids: set[str]) -> dict[str, Any]:
    if not isinstance(document, dict) or document.get("format") != "civiccal.normalized-events.v1":
        raise ValueError("Input must use civiccal.normalized-events.v1.")
    source_id = document.get("source_id")
    if source_id not in school_source_ids:
        raise ValueError(f"Source {source_id!r} is not registered as a school source.")
    result = json.loads(json.dumps(document))
    for event in result.get("events", []):
        event["school_schedule"] = classify_event(event)
    result["school_schedule_summary"] = {
        "format": FORMAT,
        "classified_exceptions": sum(
            bool(event["school_schedule"]["is_schedule_exception"])
            for event in result.get("events", [])
        ),
        "event_count": len(result.get("events", [])),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Normalized event JSON file")
    parser.add_argument("--registry", default="data/sources.json")
    parser.add_argument("--output", help="Output path; defaults to stdout")
    args = parser.parse_args()
    try:
        document = json.loads(Path(args.input).read_text(encoding="utf-8"))
        registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
        result = classify_document(document, _school_source_ids(registry))
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        print(
            f"Classified {result['school_schedule_summary']['classified_exceptions']} "
            f"schedule exception(s) among {result['school_schedule_summary']['event_count']} events.",
            file=sys.stderr,
        )
        return 0
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
