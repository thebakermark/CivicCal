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
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class FeedError(Exception):
    """Invalid publication manifest or event representation."""


def _escape(value: Any) -> str:
    text = str(value or "")
    escaped: list[str] = []
    for char in text:
        if char == "\\":
            escaped.append("\\\\")
        elif char == ";":
            escaped.append("\\;")
        elif char == ",":
            escaped.append("\\,")
        elif char in "\r\n":
            if char == "\r":
                continue
            escaped.append("\\n")
        else:
            escaped.append(char)
    return "".join(escaped)

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


def _temporal(value: Any, time_status: str, field: str, tzid: str | None = None) -> tuple[str, str]:
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
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            return "", parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if time_status == "utc":
            return "", parsed.replace(tzinfo=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if time_status == "zoned" and tzid:
            try:
                zone = ZoneInfo(tzid)
            except (ZoneInfoNotFoundError, ValueError) as exc:
                raise FeedError(f"{field} has unknown IANA timezone {tzid!r}.") from exc
            first = parsed.replace(tzinfo=zone, fold=0)
            second = parsed.replace(tzinfo=zone, fold=1)
            first_valid = first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == parsed
            second_valid = second.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == parsed
            if not first_valid and not second_valid:
                raise FeedError(f"{field} is a nonexistent local time in {tzid!r}.")
            if first.utcoffset() != second.utcoffset():
                raise FeedError(
                    f"{field} is ambiguous during a daylight-saving transition in {tzid!r}; "
                    "an explicit UTC offset is required."
                )
            return f"TZID={tzid}", parsed.strftime("%Y%m%dT%H%M%S")
        raise FeedError(f"{field} is zoned but has no explicit UTC offset or valid IANA timezone.")
    raise FeedError(f"{field} has unsupported time status {time_status!r}.")


def _offset_text(value: timedelta) -> str:
    seconds = int(value.total_seconds())
    sign = "+" if seconds >= 0 else "-"
    seconds = abs(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds_remainder = divmod(remainder, 60)
    if seconds_remainder:
        return f"{sign}{hours:02d}{minutes:02d}{seconds_remainder:02d}"
    return f"{sign}{hours:02d}{minutes:02d}"


def _timezone_component(tzid: str, years: set[int]) -> list[str]:
    """Build bounded explicit VTIMEZONE observances from the system IANA database."""
    try:
        zone = ZoneInfo(tzid)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise FeedError(f"Unknown IANA timezone {tzid!r}.") from exc
    if not years:
        raise FeedError("Cannot build VTIMEZONE without event years.")
    if min(years) < 2 or max(years) > 9998:
        raise FeedError("IANA timezone publication supports event years 0002 through 9998.")
    first_year = max(2, min(years) - 1)
    last_year = min(9998, max(years) + 2)
    start_utc = datetime(first_year, 1, 1, tzinfo=timezone.utc)
    end_utc = datetime(last_year + 1, 1, 1, tzinfo=timezone.utc)
    step = timedelta(hours=6)
    transitions = []
    cursor = start_utc
    previous = cursor.astimezone(zone)
    while cursor < end_utc:
        next_cursor = min(cursor + step, end_utc)
        current = next_cursor.astimezone(zone)
        if (previous.utcoffset(), previous.tzname()) != (current.utcoffset(), current.tzname()):
            low, high = cursor, next_cursor
            old_offset, old_name = previous.utcoffset(), previous.tzname()
            while (high - low).total_seconds() > 1:
                mid = low + timedelta(seconds=int((high - low).total_seconds() // 2))
                probe = mid.astimezone(zone)
                if (probe.utcoffset(), probe.tzname()) == (old_offset, old_name):
                    low = mid
                else:
                    high = mid
            instant = high
            before = (instant - timedelta(seconds=1)).astimezone(zone)
            after = instant.astimezone(zone)
            old, new = before.utcoffset(), after.utcoffset()
            if old is None or new is None:
                raise FeedError(f"Timezone {tzid!r} has an unresolved offset transition.")
            local_transition = (instant + old).replace(tzinfo=None)
            transitions.append((local_transition, old, new, after.tzname() or tzid))
        cursor, previous = next_cursor, current

    groups = {}
    for local, old, new, name in transitions:
        kind = "DAYLIGHT" if new > old else "STANDARD"
        key = (kind, _offset_text(old), _offset_text(new), name)
        groups.setdefault(key, []).append(local)

    if not groups:
        fixed = datetime(first_year, 1, 1, tzinfo=zone)
        offset = fixed.utcoffset()
        if offset is None:
            raise FeedError(f"Timezone {tzid!r} has no resolvable UTC offset.")
        groups[("STANDARD", _offset_text(offset), _offset_text(offset), fixed.tzname() or tzid)] = [
            datetime(first_year, 1, 1)
        ]

    lines = ["BEGIN:VTIMEZONE", f"TZID:{_escape(tzid)}"]
    for (kind, old, new, name), dates in sorted(groups.items()):
        dates.sort()
        lines.extend([
            f"BEGIN:{kind}",
            f"DTSTART:{dates[0].strftime('%Y%m%dT%H%M%S')}",
            f"TZOFFSETFROM:{old}",
            f"TZOFFSETTO:{new}",
            f"TZNAME:{_escape(name)}",
        ])
        if len(dates) > 1:
            lines.append("RDATE:" + ",".join(item.strftime("%Y%m%dT%H%M%S") for item in dates[1:]))
        lines.append(f"END:{kind}")
    lines.append("END:VTIMEZONE")
    return lines


def _event_year(value: Any) -> int | None:
    if not isinstance(value, dict) or not isinstance(value.get("value"), str):
        return None
    try:
        return int(value["value"][:4])
    except (TypeError, ValueError):
        return None


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
    tzid = current.get("timezone") if isinstance(current.get("timezone"), str) else None
    start_param, start_value = _temporal(current.get("start"), time_status, "start", tzid)
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
        end_param, end_value = _temporal(end, time_status, "end", tzid)
        if end_param != start_param:
            raise FeedError(f"{event_id}: DTSTART and DTEND value types do not match.")
        if start_param == "VALUE=DATE":
            # Never guess whether a publisher's all-day end date is inclusive.
            if current.get("end_exclusive") is not True:
                raise FeedError(
                    f"{event_id}: all-day end date is ambiguous; "
                    "set end_exclusive=true only when source semantics establish it."
                )
            lines.append(f"DTEND;{end_param}:{end_value}")
        elif end_param:
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
    elif status in {"scheduled", "rescheduled"}:
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

    records_by_id = {}
    for identity_key, record in identity_state["events"].items():
        if not isinstance(record, dict):
            raise FeedError(f"Identity record {identity_key!r} must be an object.")
        event_id = record.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise FeedError(f"Identity record {identity_key!r} has no valid event_id.")
        if event_id in records_by_id:
            raise FeedError(f"Identity state contains duplicate event ID {event_id!r}.")
        if not isinstance(record.get("source_id"), str) or not record["source_id"].strip():
            raise FeedError(f"Identity record {event_id!r} has no valid source_id.")
        records_by_id[event_id] = record
    missing = [event_id for event_id in approved if event_id not in records_by_id]
    if missing:
        raise FeedError("Approved event IDs not found in identity state: " + ", ".join(missing))

    name = manifest.get("calendar_name") or "CivicCal Community Calendar"
    return build_calendar_records(records_by_id, approved, name)


def build_calendar_records(records_by_id: dict, approved: list[str], name: str) -> tuple[str, dict]:
    """Render an already source-scoped set of approved event records."""
    if not isinstance(name, str) or not name.strip():
        raise FeedError("calendar_name must be a non-empty string.")
    if not isinstance(approved, list) or any(not isinstance(item, str) or not item for item in approved):
        raise FeedError("approved event IDs must be non-empty strings.")
    if len(set(approved)) != len(approved):
        raise FeedError("approved event IDs contain duplicates.")
    missing = [event_id for event_id in approved if event_id not in records_by_id]
    if missing:
        raise FeedError("Approved event IDs not found in records: " + ", ".join(missing))
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CivicCal//Community Calendar//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(name)}",
        "METHOD:PUBLISH",
    ]
    timezone_years = {}
    for event_id in approved:
        current = records_by_id[event_id].get("current") or {}
        tzid = current.get("timezone")
        start = current.get("start")
        raw_start = start.get("value") if isinstance(start, dict) else None
        has_explicit_offset = isinstance(raw_start, str) and (
            raw_start.endswith("Z") or bool(re.search(r"[+-]\\d{2}:?\\d{2}$", raw_start))
        )
        if current.get("time_status") == "zoned" and isinstance(tzid, str) and tzid and not has_explicit_offset:
            years = {year for year in (_event_year(start), _event_year(current.get("end"))) if year is not None}
            if years:
                timezone_years.setdefault(tzid, set()).update(years)
    for tzid, years in sorted(timezone_years.items()):
        lines.extend(_timezone_component(tzid, years))
    for event_id in approved:
        lines.extend(_event_lines(event_id, records_by_id[event_id]))
    lines.append("END:VCALENDAR")
    rendered = "\\r\\n".join(_fold(line) for line in lines) + "\\r\\n"
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
