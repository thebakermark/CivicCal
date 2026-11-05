#!/usr/bin/env python3
"""Deterministic, offline normalization of CivicCal parser-result JSON.

The original parser event is retained verbatim in source_record. This stage
never fetches, reconciles identities, merges duplicates, writes a database,
or publishes events.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

FORMATS = {"civiccal.parse-result.v1", "civiccal.normalized-events.v1", "civiccal.manual-events.v1"}
DATE_FORMATS = ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y",
                "%A, %B %d, %Y", "%A, %b %d, %Y",
                "%A %B %d, %Y", "%A %b %d, %Y")
TIME_RANGE = re.compile(
    r"^\s*(\d{1,2}(?::\d{2})?\s*[AP]M)\s*(?:-|–|—|to)\s*"
    r"(\d{1,2}(?::\d{2})?\s*[AP]M)\s*$", re.IGNORECASE
)
TIME_SINGLE = re.compile(r"^\s*(\d{1,2}(?::\d{2})?\s*[AP]M)\s*$", re.IGNORECASE)


class NormalizationError(Exception):
    """Invalid input envelope or unsupported data shape."""


def parse_date_text(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    raw = " ".join(value.replace(",", ",").split())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def parse_time_text(value: Any) -> tuple[time, time | None] | None:
    if not isinstance(value, str):
        return None
    match = TIME_RANGE.match(value)
    single = TIME_SINGLE.match(value) if not match else None
    if not match and not single:
        return None

    def parse_clock(raw: str) -> time:
        compact = raw.upper().replace(" ", "")
        return datetime.strptime(compact, "%I:%M%p" if ":" in compact else "%I%p").time()

    try:
        if single:
            return parse_clock(single.group(1)), None
        assert match is not None
        return parse_clock(match.group(1)), parse_clock(match.group(2))
    except ValueError:
        return None


def normalize_temporal(value: Any) -> tuple[dict | None, str]:
    """Return (canonical temporal object, time_status); never infer a zone."""
    if value is None:
        return None, "unresolved"
    if isinstance(value, dict):
        raw = value.get("value")
        kind = value.get("kind")
        if kind == "date" and isinstance(raw, str):
            try:
                parsed = date.fromisoformat(raw)
                return {"value": parsed.isoformat(), "kind": "date",
                        "timezone": None, "utc_offset": None}, "date_only"
            except ValueError:
                return {"value": raw, "kind": "unparsed",
                        "timezone": value.get("timezone"), "utc_offset": None}, "unresolved"
        if kind == "date-time" and isinstance(raw, str):
            try:
                parsed = datetime.fromisoformat(raw)
                tzid = value.get("timezone")
                utc = bool(value.get("utc")) or tzid == "UTC"
                offset = parsed.strftime("%z") if parsed.tzinfo else None
                return {"value": parsed.isoformat(), "kind": "date-time",
                        "timezone": tzid if tzid and tzid != "UTC" else None,
                        "utc_offset": offset}, "utc" if utc else ("zoned" if tzid else "floating")
            except ValueError:
                return {"value": raw, "kind": "unparsed",
                        "timezone": value.get("timezone"), "utc_offset": None}, "unresolved"
        if kind == "unparsed":
            return {"value": raw, "kind": "unparsed",
                    "timezone": value.get("timezone"), "utc_offset": None}, "unresolved"
        return None, "unresolved"
    if isinstance(value, str):
        raw = value.strip()
        try:
            parsed_date = date.fromisoformat(raw)
            return {"value": parsed_date.isoformat(), "kind": "date",
                    "timezone": None, "utc_offset": None}, "date_only"
        except ValueError:
            pass
        try:
            parsed_dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            is_utc = raw.endswith("Z")
            offset = parsed_dt.strftime("%z") if parsed_dt.tzinfo else None
            return {"value": parsed_dt.isoformat(), "kind": "date-time",
                    "timezone": None, "utc_offset": offset}, "utc" if is_utc else ("zoned" if offset else "floating")
        except ValueError:
            return None, "unresolved"
    return None, "unresolved"


def _location(value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, str):
        return {"name": value.strip() or None}
    if isinstance(value, list):
        return {"source_text": copy.deepcopy(value)}
    if isinstance(value, dict):
        # Preserve the publisher's address object; don't geocode or infer parts.
        return copy.deepcopy(value)
    return {"source_value": copy.deepcopy(value)}


def _description(event: dict) -> str | None:
    value = event.get("description")
    if isinstance(value, list):
        return "\n".join(str(x) for x in value if x is not None) or None
    return value if isinstance(value, str) else None


def _registration(event: dict) -> str | None:
    for link in event.get("links", []) if isinstance(event.get("links"), list) else []:
        if not isinstance(link, dict):
            continue
        label = str(link.get("text") or "").casefold()
        if any(word in label for word in ("register", "registration", "sign up", "enroll")):
            return link.get("url")
    offers = event.get("offers")
    if isinstance(offers, list):
        for offer in offers:
            if isinstance(offer, dict) and offer.get("url"):
                return offer["url"]
    return None


def _status(event: dict) -> str:
    raw = str(event.get("status") or "").casefold()
    if event.get("cancelled") is True or "cancel" in raw:
        return "cancelled"
    if "postpon" in raw:
        return "postponed"
    if "reschedul" in raw:
        return "rescheduled"
    if not raw or raw in {"confirmed", "scheduled", "eventscheduled"}:
        return "scheduled"
    if raw in {"tentative", "eventtentative"}:
        return "unknown"
    return "unknown"


def normalize_event(event: dict, source_id: str, capture: dict | None = None) -> dict:
    if not isinstance(event, dict):
        raise NormalizationError("Each parser event must be a JSON object.")

    flags: list[str] = []
    raw_start = event.get("start")
    raw_end = event.get("end")
    start, start_status = normalize_temporal(raw_start)
    end, end_status = normalize_temporal(raw_end)

    # Reviewed source-specific text formats: only fully specified dates and
    # explicit AM/PM ranges are converted. All original text remains untouched.
    date_text = event.get("date_text") or event.get("start_text")
    if start is None and date_text:
        parsed_date = parse_date_text(date_text)
        if parsed_date:
            times = parse_time_text(event.get("time_text"))
            if times:
                start_dt = datetime.combine(parsed_date, times[0])
                start = {"value": start_dt.isoformat(timespec="minutes"),
                         "kind": "date-time", "timezone": None, "utc_offset": None}
                if times[1] is not None:
                    end_dt = datetime.combine(parsed_date, times[1])
                    end = {"value": end_dt.isoformat(timespec="minutes"),
                           "kind": "date-time", "timezone": None, "utc_offset": None}
                start_status = "floating"
                end_status = "floating" if end is not None else "unresolved"
            else:
                start = {"value": parsed_date.isoformat(), "kind": "date",
                         "timezone": None, "utc_offset": None}
                start_status = "date_only"
        else:
            flags.append("event_date_unresolved")
    if start is None:
        flags.append("event_start_missing_or_unparseable")
    if not event.get("title") or not str(event.get("title")).strip():
        flags.append("title_missing")

    all_day = (event.get("all_day") is True) or bool(start and start["kind"] == "date")
    if end and start and end["kind"] == start["kind"] == "date-time":
        try:
            if datetime.fromisoformat(end["value"]) < datetime.fromisoformat(start["value"]):
                flags.append("end_before_start")
        except (TypeError, ValueError):
            # Floating and zoned datetimes cannot be ordered without guessing a zone.
            flags.append("temporal_comparison_unavailable")

    raw_location = event.get("location")
    if raw_location is None:
        raw_location = event.get("location_text")
    location = _location(raw_location)
    if not location:
        flags.append("location_missing")

    categories = event.get("categories")
    if not isinstance(categories, list):
        categories = []
    offers = event.get("offers") if isinstance(event.get("offers"), list) else []
    fee_text = event.get("fee_text") or []
    cost_text = "; ".join(str(x) for x in fee_text) if isinstance(fee_text, list) else str(fee_text or "")
    if not cost_text:
        prices = [str(o.get("price")) for o in offers if isinstance(o, dict) and o.get("price") is not None]
        cost_text = "; ".join(prices) or None

    record = {
        "source_id": source_id,
        "source_event_id": event.get("uid") or event.get("cid"),
        "title": str(event.get("title")).strip() if event.get("title") is not None else None,
        "description": _description(event),
        "start": start,
        "end": end,
        "end_exclusive": event.get("end_exclusive") if isinstance(event.get("end_exclusive"), bool) else None,
        "all_day": all_day,
        "time_status": start_status,
        "timezone": start.get("timezone") if start else None,
        "location": location,
        "event_url": event.get("event_url") or event.get("url") or event.get("source_url"),
        "registration_url": _registration(event),
        "registration_deadline": copy.deepcopy(event.get("registration_deadline_text") or None),
        "cost_text": cost_text,
        "is_free": event.get("is_accessible_for_free") if isinstance(event.get("is_accessible_for_free"), bool) else None,
        "status": _status(event),
        "attendance_mode": event.get("event_attendance_mode"),
        "audience": copy.deepcopy(event.get("audience") or event.get("age_groups")),
        "registration_required": event.get("registration_required") if isinstance(event.get("registration_required"), bool) else None,
        "registration_status": event.get("registration_status"),
        "organizer": copy.deepcopy(event.get("organizer")),
        "image_url": event.get("image"),
        "categories": copy.deepcopy(categories),
        "recurrence": {
            "rule": event.get("recurrence_rule"),
            "dates": copy.deepcopy(event.get("recurrence_dates") or []),
            "exceptions": copy.deepcopy(event.get("exception_dates") or []),
            "instance_id": event.get("recurrence_id"),
        } if any(event.get(k) for k in ("recurrence_rule", "recurrence_dates", "exception_dates", "recurrence_id")) else None,
        "data_quality_flags": flags,
        "source_record": copy.deepcopy(event),
        "capture": copy.deepcopy(capture) if capture else None,
    }
    if event.get("registration_deadline_text"):
        record["data_quality_flags"].append("registration_deadline_preserved_as_source_text")
    if event.get("event_date_year_known") is False and date_text:
        record["data_quality_flags"].append("source_date_year_not_explicit")
    if start_status == "floating":
        record["data_quality_flags"].append("timezone_not_assigned")
    if start_status == "unresolved":
        record["data_quality_flags"].append("time_semantics_unresolved")
    return record


def normalize_document(document: dict) -> dict:
    if not isinstance(document, dict):
        raise NormalizationError("Input must be a JSON object.")
    if document.get("format") == "civiccal.parse-result.v1":
        source_id = document.get("source_id")
        parser_output = document.get("parser_output")
        capture = document.get("capture")
    elif document.get("format") == "civiccal.manual-events.v1":
        source_id = document.get("source_id")
        if not isinstance(document.get("observed_at"), str) or not document["observed_at"].strip():
            raise NormalizationError("Manual event snapshots require observed_at.")
        if not isinstance(document.get("source_url"), str) or not document["source_url"].startswith("https://"):
            raise NormalizationError("Manual event snapshots require an HTTPS source_url.")
        parser_output = document
        capture = {
            "capture_method": "manual-public-page-review",
            "observed_at": document["observed_at"],
            "source_url": document["source_url"],
            "observation_note": document.get("observation_note"),
            "content_sha256": None,
        }
    elif document.get("format") in {"civiccal.ics.v1", "civiccal.html-events.v1",
                                    "civiccal.park-district-events.v1", "civiccal.village-events.v1"}:
        source_id = document.get("source_id")
        parser_output = document
        capture = None
    else:
        raise NormalizationError("Unsupported parser-result format.")

    if not isinstance(source_id, str) or not source_id.strip():
        raise NormalizationError("Parser result has no source_id.")
    if not isinstance(parser_output, dict) or not isinstance(parser_output.get("events"), list):
        raise NormalizationError("Parser output must contain an events array.")

    normalized = [normalize_event(item, source_id, capture) for item in parser_output["events"]]
    warnings = list(parser_output.get("warnings") or [])
    return {
        "format": "civiccal.normalized-events.v1",
        "source_id": source_id,
        "capture": copy.deepcopy(capture),
        "parser_format": parser_output.get("format"),
        "source_event_count": len(parser_output["events"]),
        "event_count": len(normalized),
        "events": normalized,
        "parser_warnings": warnings,
        "summary": {
            "events_with_review_flags": sum(bool(e["data_quality_flags"]) for e in normalized),
            "flag_counts": {
                flag: sum(flag in e["data_quality_flags"] for e in normalized)
                for flag in sorted({f for e in normalized for f in e["data_quality_flags"]})
            },
        },
        "rules": [
            "Source records are preserved verbatim in source_record.",
            "Unspecified timezones are never inferred.",
            "Undated and incomplete records are retained with review flags.",
            "No identity reconciliation, duplicate merging, storage, or publication occurs.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Parser-result JSON path, or - for stdin")
    parser.add_argument("--output", help="Output JSON path; defaults to stdout")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        result = normalize_document(json.loads(raw))
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        print(f"Normalized {result['event_count']} event record(s); "
              f"{result['summary']['events_with_review_flags']} need review.", file=sys.stderr)
        return 0
    except (OSError, json.JSONDecodeError, NormalizationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
