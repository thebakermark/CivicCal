#!/usr/bin/env python3
"""Find exact-content duplicate candidates in CivicCal normalized ICS JSON.

This is a review aid only: it never merges, deletes, or rewrites events.
UID and source metadata are deliberately excluded from the content signature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value))
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text or None


def signature_for(event: dict[str, Any]) -> dict[str, Any]:
    """Return conservative event-content fields used for exact candidate matching."""
    return {
        "title": normalize_text(event.get("title")),
        "description": normalize_text(event.get("description")),
        "location": normalize_text(event.get("location")),
        "start": event.get("start"),
        "end": event.get("end"),
        "status": normalize_text(event.get("status") or "CONFIRMED"),
    }


def find_duplicate_candidates(document: dict[str, Any]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, event in enumerate(document.get("events", [])):
        signature = signature_for(event)
        # Events without a title or start cannot be matched safely.
        if not signature["title"] or not signature["start"]:
            continue
        encoded = json.dumps(signature, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        groups[digest].append({
            "event_index": index,
            "uid": event.get("uid"),
            "source_id": event.get("source_id"),
            "title": event.get("title"),
            "start": event.get("start"),
            "end": event.get("end"),
            "location": event.get("location"),
        })

    candidates = [
        {"signature": digest, "count": len(records), "records": records}
        for digest, records in sorted(groups.items())
        if len(records) > 1
    ]
    return {
        "format": "civiccal.duplicate-candidates.v1",
        "source_event_count": len(document.get("events", [])),
        "candidate_group_count": len(candidates),
        "candidate_record_count": sum(group["count"] for group in candidates),
        "excess_record_count": sum(group["count"] - 1 for group in candidates),
        "groups": candidates,
        "note": "Review candidates manually. No events have been merged or removed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Find exact-content duplicate candidates in CivicCal normalized ICS JSON.")
    parser.add_argument("input", help="Normalized JSON file, or - for standard input")
    parser.add_argument("--output", help="JSON output path; defaults to stdout")
    args = parser.parse_args()
    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
    result = find_duplicate_candidates(json.loads(raw))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
