#!/usr/bin/env python3
"""Generate a deterministic RFC 5545 feed from explicitly approved identity records.

This is an offline projection. It does not approve events, fetch sources, mutate
identity state, or publish over a network.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class FeedError(Exception):
    """Invalid publication manifest or event representation."""


def _escape(value: Any) -> str:
    text = str(value or "")
    return (text.replace("\\", "\\\\")
                .replace(";", "\\;")
                .replace(",", "\\,")
                .replace("\r\n", "\\n")
                .replace("\n", "\\n")
                .replace("\r", "\\n"))


def _fold(line: str) -> str:
    """Fold a content line at 75 UTF-8 octets, including continuation space."""
    chunks: list[str] = []
    current = ""
    limit = 75
    for char in line:
        encoded = (current + char).encode("utf-8")
        if len(encoded) > limit and current:
            chunks.append(current)
            current = " " + char
            limit = 75
        else:
            current += char
    chunks.append(current)
    return "\r\n".join(chunks)


def _utc_stamp(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise FeedError(f"{field} must be an ISO 8601 UTC timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeedError(f"{field} is not a valid ISO 8601 timestamp.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FeedError(f"{field} must include a UTC offset.")
    return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _temporal(value: Any, time_status: str, field: str) -> tuple[str, str]:
    if not isinstance(value, dict) or not isinstance(value.get("value"), str):
        raise FeedError(f"Approved event is missing a valid {field}.")
    kind = value.get("kind")
    raw = value["value"]
    if kind == "date":
        try:
            return "VALUE=DATE", date.fromisoformat(raw).strftime("%Y%m%d")
        except ValueError as exc:
            raise FeedError(f"{field} has an invalid date.") from exc
    if kind != "date-time":
        raise FeedError(f"{field} has unsupported or unresolved time semantics.")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeedError(f"{field} has an invalid date-time.") from exc
    if time_status == "floating":
        if parsed.tzinfo is not None:
            raise FeedError(f"{field} is marked floating but contains an offset.")
        return "", parsed.strftime("%Y%m%dT%H%M%S")
    if time_status in {"utc", "zoned"}:
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise FeedError(
                f"{field} is zoned but has no explicit UTC offset; "
                "TZID/VTIMEZONE publication is not implemented yet."
            )
        return "", parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raise FeedError(f"{field} has unsupported time status {time_status!r}.")


def _valid_url(value: Any, field: str) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise FeedError(f"{field} must be a URL string.")
    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc or parsed.username or parsed.password:
        raise FeedError(f"{field} must be an absolute HTTP(S) URL without credentials.")
    return value


def _event_lines(event_id: str, record: dict) -> list[str]:
    current = record.get("current")
    if not isinstance(current, dict):
        raise FeedError(f"{event_id}: identity record has no current event.")
    title = current.get("title")
    if not isinstance(title, str) or not title.strip():
        raise FeedError(f"{event_id}: approved event has no title.")
    revision = record.get("revisions")
    if not isinstance(revision, list) or not revision:
        raise FeedError(f"{event_id}: identity record has no revision history.")
    revision_number = revision[-1].get("revision")
    if not isinstance(revision_number, int) or revision_number < 1:
        raise FeedError(f"{event_id}: invalid revision number.")
    stamp = _utc_stamp(revision[-1].get("observed_at"), f"{event_id} revision observed_at")
    time_status = current.get("time_status") or "unresolved"
    start_param, start_value = _temporal(current.get("start"), time_status, "start")
    lines = [
        "BEGIN:VEVENT",
        f"UID:{_escape(event_id)}@civiccal",
        f"DTSTAMP:{stamp}",
        f"LAST-MODIFIED:{stamp}",
        f"SEQUENCE:{revision_number}",
        f"SUMMARY:{_escape(title)}",
    ]
    if start_param:
        lines.append(f"DTSTART;{start_param}:{start_value}")
    else:
        lines.append(f"DTSTART:{start_value}")

    end = current.get("end")
    if end is not None:
        end_param, end_value = _temporal(end, time_status, "end")
        if end_param != start_param:
            raise FeedError(f"{event_id}: DTSTART and DTEND value types do not match.")
        if start_param:
            # All-day DTEND is emitted only when explicitly marked exclusive.
            if current.get("end_exclusive") is True:
                lines.append(f"DTEND;{end_param}:{end_value}")
        else:
            lines.append(f"DTEND:{end_value}")

    description = current.get("description")
    if description:
        lines.append(f"DESCRIPTION:{_escape(description)}")
    location = current.get("location")
    if isinstance(location, dict):
        location = location.get("name") or location.get("source_text")
    if isinstance(location, list):
        location = ", ".join(str(item) for item in location)
    if location:
        lines.append(f"LOCATION:{_escape(location)}")
    categories = current.get("categories")
    if isinstance(categories, list) and categories:
        lines.append("CATEGORIES:" + ",".join(_escape(item) for item in categories))
    event_url = _valid_url(current.get("event_url"), "event_url")
    registration_url = _valid_url(current.get("registration_url"), "registration_url")
    if event_url:
        lines.append(f"URL:{event_url}")
    if registration_url:
        lines.append(f"X-CIVICCAL-REGISTRATION-URL:{registration_url}")
    source_id = record.get("source_id")
    if source_id:
        lines.append(f"X-CIVICCAL-SOURCE-ID:{_escape(source_id)}")
    status = current.get("status")
    if status == "cancelled":
        lines.append("STATUS:CANCELLED")
    elif status in {"scheduled", "postponed", "rescheduled"}:
        lines.append("STATUS:CONFIRMED")
    if current.get("recurrence"):
        raise FeedError(
            f"{event_id}: recurrence is present; recurrence-aware feed projection "
            "must be implemented before publishing this event."
        )
    lines.append("END:VEVENT")
    return lines


def build_calendar(identity_state: dict, manifest: dict) -> tuple[str, dict]:
    if not isinstance(identity_state, dict) or identity_state.get("format") != "civiccal.identity-state.v1":
        raise FeedError("Identity input must use civiccal.identity-state.v1.")
    if not isinstance(identity_state.get("events"), dict):
        raise FeedError("Identity state events must be an object.")
    if not isinstance(manifest, dict) or manifest.get("format") != "civiccal.publication-manifest.v1":
        raise FeedError("Publication manifest must use civiccal.publication-manifest.v1.")
    approved = manifest.get("approved_event_ids")
    if not isinstance(approved, list) or any(not isinstance(item, str) or not item for item in approved):
        raise FeedError("approved_event_ids must be an array of non-empty event IDs.")
    if len(set(approved)) != len(approved):
        raise FeedError("Publication manifest contains duplicate event IDs.")

    records_by_id = {
        record.get("event_id"): record
        for record in identity_state["events"].values()
        if isinstance(record, dict) and isinstance(record.get("event_id"), str)
    }
    missing = [event_id for event_id in approved if event_id not in records_by_id]
    if missing:
        raise FeedError("Approved event IDs not found in identity state: " + ", ".join(missing))

    name = manifest.get("calendar_name") or "CivicCal Community Calendar"
    if not isinstance(name, str) or not name.strip():
        raise FeedError("calendar_name must be a non-empty string.")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CivicCal//Community Calendar//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(name)}",
        "METHOD:PUBLISH",
    ]
    for event_id in approved:
        lines.extend(_event_lines(event_id, records_by_id[event_id]))
    lines.append("END:VCALENDAR")
    rendered = "\r\n".join(_fold(line) for line in lines) + "\r\n"
    return rendered, {
        "approved_count": len(approved),
        "published_count": len(approved),
        "event_ids": approved,
        "format": "text/calendar; charset=utf-8",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity_state", help="Identity state JSON path")
    parser.add_argument("publication_manifest", help="Explicit publication approval manifest JSON path")
    parser.add_argument("--output", required=True, help="Output .ics path")
    args = parser.parse_args()
    try:
        state = json.loads(Path(args.identity_state).read_text(encoding="utf-8"))
        manifest = json.loads(Path(args.publication_manifest).read_text(encoding="utf-8"))
        rendered, summary = build_calendar(state, manifest)
        Path(args.output).write_bytes(rendered.encode("utf-8"))
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    except (OSError, json.JSONDecodeError, FeedError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
