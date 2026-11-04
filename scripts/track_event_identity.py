#!/usr/bin/env python3
"""Offline, deterministic source-event identity and revision tracker.

Only publisher-provided source_event_id values create stable tracked identities.
Records without one are retained as unkeyed observations for review. This tool
never merges events across sources or treats disappearance as cancellation.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATE_FORMAT = "civiccal.identity-state.v1"
RESULT_FORMAT = "civiccal.identity-result.v1"
MATERIAL_FIELDS = (
    "title", "description", "start", "end", "all_day", "time_status",
    "timezone", "location", "event_url", "registration_url",
    "registration_deadline", "cost_text", "is_free", "status",
    "attendance_mode", "audience", "organizer", "image_url", "categories",
    "recurrence",
)


class IdentityError(Exception):
    """Invalid state or normalized event input."""


def _json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _identity_key(source_id: str, source_event_id: str,
                  recurrence_instance: Any = None) -> str:
    return _json_hash({
        "source_id": source_id,
        "source_event_id": source_event_id,
        "recurrence_instance": recurrence_instance,
    })


def _material_projection(event: dict) -> dict:
    return {field: copy.deepcopy(event.get(field)) for field in MATERIAL_FIELDS}


def _valid_state(state: Any) -> dict:
    if state is None:
        return {"format": STATE_FORMAT, "events": {}, "unkeyed_observations": [],
                "processed_captures": []}
    if not isinstance(state, dict) or state.get("format") != STATE_FORMAT:
        raise IdentityError("State file must use civiccal.identity-state.v1.")
    if not isinstance(state.get("events"), dict):
        raise IdentityError("State events must be an object.")
    if not isinstance(state.get("unkeyed_observations"), list):
        raise IdentityError("State unkeyed_observations must be an array.")
    if not isinstance(state.get("processed_captures"), list):
        raise IdentityError("State processed_captures must be an array.")
    return copy.deepcopy(state)


def _capture_key(document: dict) -> str:
    capture = document.get("capture") or {}
    for field in ("capture_id", "content_sha256", "payload_sha256"):
        value = capture.get(field) if isinstance(capture, dict) else None
        if value:
            return str(value)
    # Direct parser fixtures and manually supplied normalized files may not
    # have capture metadata. Use their stable normalized content as the key.
    return _json_hash({
        "source_id": document.get("source_id"),
        "events": [
            {"source_event_id": e.get("source_event_id"),
             "material": _material_projection(e),
             "source_record": e.get("source_record")}
            for e in document.get("events", [])
        ],
    })


def process_normalized(document: dict, prior_state: dict | None = None,
                       observed_at: str | None = None) -> tuple[dict, dict]:
    if not isinstance(document, dict) or document.get("format") != "civiccal.normalized-events.v1":
        raise IdentityError("Input must use civiccal.normalized-events.v1.")
    source_id = document.get("source_id")
    events = document.get("events")
    if not isinstance(source_id, str) or not source_id.strip():
        raise IdentityError("Normalized document has no source_id.")
    if not isinstance(events, list) or any(not isinstance(e, dict) for e in events):
        raise IdentityError("Normalized document events must be an array of objects.")

    state = _valid_state(prior_state)
    timestamp = observed_at or _now()
    capture_key = _capture_key(document)
    capture_token = _json_hash({"source_id": source_id, "capture_key": capture_key})
    already_processed = capture_token in state["processed_captures"]
    if already_processed:
        return ({
            "format": RESULT_FORMAT, "source_id": source_id,
            "capture_key": capture_key, "already_processed": True,
            "new_events": 0, "new_revisions": 0, "unchanged_events": 0,
            "unkeyed_count": 0, "identity_conflicts": [],
            "events": [], "unkeyed_observations": [],
            "note": "This source capture was already processed; state is unchanged.",
        }, state)

    # A source ID is deliberately required. A publisher ID is not globally
    # unique, so the stable key is always scoped to the registered source.
    keyed: dict[str, list[dict]] = {}
    unkeyed: list[dict] = []
    for index, event in enumerate(events):
        publisher_id = event.get("source_event_id")
        if publisher_id is None or not str(publisher_id).strip():
            unkeyed.append({
                "identity_status": "unresolved",
                "source_id": source_id,
                "source_event_id": None,
                "observation_id": "obs_" + _json_hash({
                    "source_id": source_id, "capture_key": capture_key,
                    "index": index, "event": event,
                })[:24],
                "observed_at": timestamp,
                "event": copy.deepcopy(event),
                "review_flags": sorted(set(event.get("data_quality_flags") or []) |
                                       {"stable_source_event_id_missing"}),
            })
            continue
        recurrence_instance = (event.get("recurrence") or {}).get("instance_id")
        key = _identity_key(source_id, str(publisher_id), recurrence_instance)
        keyed.setdefault(key, []).append(event)

    conflicts = []
    processed_events = []
    new_events = new_revisions = unchanged = 0

    for key, records in sorted(keyed.items()):
        if len(records) != 1:
            conflicts.append({
                "identity_key": key,
                "source_event_id": records[0].get("source_event_id"),
                "count": len(records),
                "reason": "multiple_records_share_source_identity_in_one_capture",
                "records": [copy.deepcopy(r) for r in records],
            })
            continue

        event = records[0]
        projection = _material_projection(event)
        fingerprint = _json_hash(projection)
        observation_id = "obs_" + _json_hash({
            "source_id": source_id, "capture_key": capture_key,
            "identity_key": key, "fingerprint": fingerprint,
        })[:24]
        existing = state["events"].get(key)
        if existing is None:
            event_id = "evt_" + key[:24]
            revision = {
                "revision": 1, "fingerprint": fingerprint,
                "observed_at": timestamp, "observation_id": observation_id,
                "change_type": "created", "values": projection,
            }
            current = {
                "event_id": event_id, "identity_key": key,
                "source_id": source_id,
                "source_event_id": str(event.get("source_event_id")),
                "recurrence_instance_id": copy.deepcopy(
                    (event.get("recurrence") or {}).get("instance_id")),
                "current": copy.deepcopy(event),
                "current_fingerprint": fingerprint,
                "first_seen_at": timestamp, "last_seen_at": timestamp,
                "observation_ids": [observation_id],
                "revisions": [revision],
            }
            state["events"][key] = current
            new_events += 1
            processed_events.append({
                "event_id": event_id, "revision": 1,
                "change_type": "created", "observation_id": observation_id,
            })
        else:
            observation_ids = existing.setdefault("observation_ids", [])
            if observation_id not in observation_ids:
                observation_ids.append(observation_id)
            existing["last_seen_at"] = timestamp
            if fingerprint == existing.get("current_fingerprint"):
                unchanged += 1
                processed_events.append({
                    "event_id": existing["event_id"],
                    "revision": len(existing.get("revisions", [])),
                    "change_type": "unchanged", "observation_id": observation_id,
                })
            else:
                revision_number = len(existing.get("revisions", [])) + 1
                revision = {
                    "revision": revision_number, "fingerprint": fingerprint,
                    "observed_at": timestamp, "observation_id": observation_id,
                    "change_type": "updated", "values": projection,
                    "previous_fingerprint": existing.get("current_fingerprint"),
                }
                existing.setdefault("revisions", []).append(revision)
                existing["current"] = copy.deepcopy(event)
                existing["current_fingerprint"] = fingerprint
                new_revisions += 1
                processed_events.append({
                    "event_id": existing["event_id"],
                    "revision": revision_number,
                    "change_type": "updated", "observation_id": observation_id,
                })

    state["unkeyed_observations"].extend(unkeyed)
    state["processed_captures"].append(capture_token)
    result = {
        "format": RESULT_FORMAT,
        "source_id": source_id,
        "capture_key": capture_key,
        "already_processed": False,
        "input_event_count": len(events),
        "new_events": new_events,
        "new_revisions": new_revisions,
        "unchanged_events": unchanged,
        "unkeyed_count": len(unkeyed),
        "identity_conflicts": conflicts,
        "events": processed_events,
        "unkeyed_observations": unkeyed,
        "missing_events_policy": "No missing or absent events are marked cancelled or deleted.",
        "cross_source_policy": "Identities are source-scoped; no cross-source merge is attempted.",
    }
    return result, state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Normalized event JSON file")
    parser.add_argument("--state", required=True, help="Identity state JSON file")
    parser.add_argument("--output", help="Result JSON path; defaults to stdout")
    parser.add_argument("--state-output", help="Updated state path; defaults to --state")
    parser.add_argument("--observed-at", help="Explicit observation timestamp (ISO 8601)")
    args = parser.parse_args()
    try:
        document = json.loads(Path(args.input).read_text(encoding="utf-8"))
        state_path = Path(args.state)
        prior = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else None
        result, state = process_normalized(document, prior, args.observed_at)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        state_rendered = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        Path(args.state_output or args.state).write_text(state_rendered, encoding="utf-8")
        print(f"New events: {result['new_events']}; revisions: {result['new_revisions']}; "
              f"unchanged: {result['unchanged_events']}; unkeyed: {result['unkeyed_count']}; "
              f"identity conflicts: {len(result['identity_conflicts'])}.", file=sys.stderr)
        return 0
    except (OSError, json.JSONDecodeError, IdentityError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
