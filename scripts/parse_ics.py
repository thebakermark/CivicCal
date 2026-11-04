#!/usr/bin/env python3
"""Dependency-free RFC 5545 VEVENT reader for CivicCal.

This parser preserves local wall times and TZID rather than guessing or
converting floating times. Recurrence rules are retained, not expanded.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def unfold_lines(text: str) -> list[str]:
    physical = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    logical: list[str] = []
    for line in physical:
        if line.startswith((" ", "\t")) and logical:
            logical[-1] += line[1:]
        elif line:
            logical.append(line)
    return logical


def split_unquoted(value: str, delimiter: str, maxsplit: int = -1) -> list[str]:
    parts, current, quoted, escaped, splits = [], [], False, False, 0
    for char in value:
        if escaped:
            current.append(char)
            escaped = False
        elif char == "\\":
            current.append(char)
            escaped = True
        elif char == '"':
            current.append(char)
            quoted = not quoted
        elif char == delimiter and not quoted and (maxsplit < 0 or splits < maxsplit):
            parts.append("".join(current))
            current = []
            splits += 1
        else:
            current.append(char)
    parts.append("".join(current))
    return parts


def unescape_text(value: str) -> str:
    out, i = [], 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            i += 1
            char = value[i]
            out.append({"n": "\n", "N": "\n", "\\": "\\", ",": ",", ";": ";"}.get(char, char))
        else:
            out.append(value[i])
        i += 1
    return "".join(out)


def parse_property(line: str) -> tuple[str, dict[str, str], str]:
    pieces = split_unquoted(line, ":", 1)
    if len(pieces) != 2:
        raise ValueError(f"Property has no value separator: {line!r}")
    left, value = pieces
    segments = split_unquoted(left, ";")
    name = segments[0].upper()
    params: dict[str, str] = {}
    for segment in segments[1:]:
        pair = split_unquoted(segment, "=", 1)
        if len(pair) == 2:
            raw_value = pair[1].strip()
            if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] == '"':
                raw_value = raw_value[1:-1]
            params[pair[0].upper()] = raw_value
    return name, params, value


def parse_datetime(value: str, params: dict[str, str]) -> dict[str, Any]:
    value_type = params.get("VALUE", "").upper()
    if value_type == "DATE" or (len(value) == 8 and "T" not in value):
        parsed = datetime.strptime(value, "%Y%m%d").date()
        return {"value": parsed.isoformat(), "kind": "date", "timezone": None, "utc": False}
    utc = value.endswith("Z")
    raw = value[:-1] if utc else value
    fmt = "%Y%m%dT%H%M%S" if len(raw) == 15 else "%Y%m%dT%H%M"
    parsed = datetime.strptime(raw, fmt)
    tzid = "UTC" if utc else params.get("TZID")
    return {
        "value": parsed.isoformat(timespec="seconds" if len(raw) == 15 else "minutes"),
        "kind": "date-time",
        "timezone": tzid,
        "utc": utc,
    }


def parse_ics(text: str, source_id: str = "unassigned", source_url: str | None = None) -> dict[str, Any]:
    lines = unfold_lines(text)
    events: list[dict[str, Any]] = []
    warnings: list[str] = []
    in_calendar = False
    current: dict[str, list[tuple[dict[str, str], str]]] | None = None
    component_depth = 0

    for line_number, line in enumerate(lines, 1):
        upper = line.upper()
        if upper == "BEGIN:VCALENDAR":
            in_calendar = True
            continue
        if upper == "END:VCALENDAR":
            in_calendar = False
            continue
        if not in_calendar:
            continue
        if upper == "BEGIN:VEVENT":
            if current is not None:
                warnings.append(f"Line {line_number}: nested VEVENT ignored")
            else:
                current = {}
                component_depth = 1
            continue
        if current is not None:
            if upper.startswith("BEGIN:"):
                component_depth += 1
                continue
            if upper.startswith("END:"):
                component_depth -= 1
                if component_depth == 0:
                    events.append(current)
                    current = None
                continue
            if component_depth != 1:
                continue
            try:
                name, params, value = parse_property(line)
                current.setdefault(name, []).append((params, value))
            except ValueError as exc:
                warnings.append(f"Line {line_number}: {exc}")

    if current is not None:
        warnings.append("Unterminated VEVENT at end of calendar")

    normalized = []
    for index, props in enumerate(events, 1):
        def values(name: str) -> list[str]:
            return [v for _, v in props.get(name, [])]

        def first(name: str, default: str | None = None) -> str | None:
            vals = values(name)
            if len(vals) > 1:
                warnings.append(f"VEVENT {index}: repeated {name}; first value used")
            return vals[0] if vals else default

        def decoded(name: str) -> str | None:
            value = first(name)
            return unescape_text(value) if value is not None else None

        def temporal(name: str) -> dict[str, Any] | None:
            entries = props.get(name, [])
            if not entries:
                return None
            try:
                return parse_datetime(entries[0][1], entries[0][0])
            except ValueError:
                warnings.append(f"VEVENT {index}: invalid {name} value {entries[0][1]!r}")
                return {"value": entries[0][1], "kind": "unparsed", "timezone": entries[0][0].get("TZID"), "utc": False}

        start = temporal("DTSTART")
        end = temporal("DTEND")
        status = (first("STATUS", "CONFIRMED") or "CONFIRMED").upper()
        normalized.append({
            "source_id": source_id,
            "source_url": source_url,
            "uid": decoded("UID"),
            "title": decoded("SUMMARY"),
            "description": decoded("DESCRIPTION"),
            "location": decoded("LOCATION"),
            "url": first("URL"),
            "organizer": first("ORGANIZER"),
            "categories": [unescape_text(v) for _, raw in props.get("CATEGORIES", []) for v in split_unquoted(raw, ",")],
            "start": start,
            "end": end,
            # RFC 5545 defines DATE-valued DTEND as non-inclusive.
            "end_exclusive": bool(end and end["kind"] == "date"),
            "all_day": bool(start and start["kind"] == "date"),
            "status": status,
            "cancelled": status == "CANCELLED",
            "recurrence_rule": first("RRULE"),
            "recurrence_dates": [v for _, v in props.get("RDATE", [])],
            "exception_dates": [v for _, v in props.get("EXDATE", [])],
            "recurrence_id": first("RECURRENCE-ID"),
            "sequence": int(first("SEQUENCE", "0") or "0") if (first("SEQUENCE", "0") or "0").isdigit() else first("SEQUENCE"),
            "last_modified": first("LAST-MODIFIED"),
            "created": first("CREATED"),
            "dtstamp": first("DTSTAMP"),
        })

    return {"format": "civiccal.ics.v1", "source_id": source_id, "event_count": len(normalized), "events": normalized, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse an ICS file into CivicCal normalized JSON.")
    parser.add_argument("input", help="ICS file path, or - for standard input")
    parser.add_argument("--source-id", default="unassigned")
    parser.add_argument("--source-url")
    parser.add_argument("--output", help="JSON output path; defaults to stdout")
    args = parser.parse_args()
    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
    result = parse_ics(raw, args.source_id, args.source_url)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
