#!/usr/bin/env python3
"""Build a deterministic read-only JSON API response from approved identity records."""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any


class QueryError(Exception):
    """Invalid API query or input document."""


PUBLIC_EVENT_FIELDS = (
    "title", "description", "start", "end", "end_exclusive", "all_day", "time_status", "timezone",
    "location", "event_url", "registration_url", "registration_deadline",
    "cost_text", "is_free", "status", "attendance_mode", "audience",
    "registration_required", "registration_status", "image_url",
    "categories",
)


def _parse_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise QueryError(f"{field} must be an ISO 8601 date (YYYY-MM-DD).") from exc


def _date_of(event: dict) -> date | None:
    start = event.get("start")
    if not isinstance(start, dict) or not isinstance(start.get("value"), str):
        return None
    try:
        return date.fromisoformat(start["value"][:10])
    except ValueError:
        return None


def _projection(record: dict) -> dict:
    current = record.get("current")
    if not isinstance(current, dict):
        raise QueryError("An approved identity record has no current event.")
    return {
        "event_id": record.get("event_id"),
        "revision": len(record.get("revisions") or []),
        "source_id": record.get("source_id"),
        "lifecycle_status": record.get("lifecycle_status") or current.get("status") or "unknown",
        "event": {field: deepcopy(current.get(field)) for field in PUBLIC_EVENT_FIELDS
                  if field in current},
    }


def query_events(identity_state: dict, manifest: dict, *,
                 start_date: str | None = None, end_date: str | None = None,
                 source_id: str | None = None, category: str | None = None,
                 q: str | None = None, limit: int = 50, offset: int = 0) -> dict:
    if not isinstance(identity_state, dict) or identity_state.get("format") != "civiccal.identity-state.v1":
        raise QueryError("Identity input must use civiccal.identity-state.v1.")
    if not isinstance(identity_state.get("events"), dict):
        raise QueryError("Identity state events must be an object.")
    if not isinstance(manifest, dict) or manifest.get("format") != "civiccal.publication-manifest.v1":
        raise QueryError("Publication manifest must use civiccal.publication-manifest.v1.")
    approved = manifest.get("approved_event_ids")
    if not isinstance(approved, list) or any(not isinstance(item, str) or not item for item in approved):
        raise QueryError("approved_event_ids must be an array of non-empty event IDs.")
    if len(set(approved)) != len(approved):
        raise QueryError("Publication manifest contains duplicate event IDs.")
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise QueryError("limit must be between 1 and 100.")
    if not isinstance(offset, int) or offset < 0:
        raise QueryError("offset must be zero or greater.")
    start_bound = _parse_date(start_date, "start_date")
    end_bound = _parse_date(end_date, "end_date")
    if start_bound and end_bound and end_bound < start_bound:
        raise QueryError("end_date cannot be earlier than start_date.")

    records = {
        record.get("event_id"): record
        for record in identity_state["events"].values()
        if isinstance(record, dict) and isinstance(record.get("event_id"), str)
    }
    missing = [event_id for event_id in approved if event_id not in records]
    if missing:
        raise QueryError("Approved event IDs not found in identity state: " + ", ".join(missing))

    needle = q.casefold().strip() if isinstance(q, str) else ""
    category_needle = category.casefold().strip() if isinstance(category, str) else ""
    selected = []
    for event_id in approved:
        item = _projection(records[event_id])
        event = item["event"]
        if source_id and item["source_id"] != source_id:
            continue
        event_date = _date_of(event)
        if start_bound and (event_date is None or event_date < start_bound):
            continue
        if end_bound and (event_date is None or event_date > end_bound):
            continue
        categories = event.get("categories") if isinstance(event.get("categories"), list) else []
        if category_needle and not any(category_needle == str(value).casefold() for value in categories):
            continue
        if needle:
            searchable = " ".join(str(event.get(field) or "") for field in ("title", "description")).casefold()
            if needle not in searchable:
                continue
        selected.append(item)

    selected.sort(key=lambda item: (
        _date_of(item["event"]) or date.max,
        item["event_id"],
    ))
    total = len(selected)
    page = selected[offset:offset + limit]
    next_offset = offset + limit if offset + limit < total else None
    return {
        "format": "civiccal.api-events.v1",
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "source_id": source_id,
            "category": category,
            "q": q,
        },
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "next_offset": next_offset,
        },
        "events": page,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("identity_state")
    parser.add_argument("publication_manifest")
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--source-id")
    parser.add_argument("--category")
    parser.add_argument("--q")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--output")
    args = parser.parse_args()
    try:
        state = json.loads(Path(args.identity_state).read_text(encoding="utf-8"))
        manifest = json.loads(Path(args.publication_manifest).read_text(encoding="utf-8"))
        result = query_events(
            state, manifest, start_date=args.start_date, end_date=args.end_date,
            source_id=args.source_id, category=args.category, q=args.q,
            limit=args.limit, offset=args.offset,
        )
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (OSError, json.JSONDecodeError, QueryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
