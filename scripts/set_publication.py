#!/usr/bin/env python3
"""Manually approve or revoke one stored event for its exact registered source.

This command changes only the publication manifest. It never captures, ingests,
edits event data, changes source permissions, or publishes over a network.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from copy import deepcopy
from pathlib import Path


class PublicationApprovalError(Exception):
    """Invalid source, identity state, or publication manifest."""


def _load_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationApprovalError(f"Cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise PublicationApprovalError(f"{label} must contain a JSON object.")
    return value


def update_publication(
    registry: dict,
    identity_state: dict,
    manifest: dict,
    source_id: str,
    event_id: str,
    action: str,
) -> tuple[dict, dict]:
    """Return an updated manifest and an auditable action summary."""
    if not isinstance(source_id, str) or not source_id.strip():
        raise PublicationApprovalError("source_id must be a non-empty string.")
    if not isinstance(event_id, str) or not event_id.strip():
        raise PublicationApprovalError("event_id must be a non-empty string.")
    if action not in {"approve", "revoke"}:
        raise PublicationApprovalError("action must be 'approve' or 'revoke'.")

    source_records = registry.get("source_records") if isinstance(registry, dict) else None
    if not isinstance(source_records, list):
        raise PublicationApprovalError("Source registry must contain a source_records array.")
    registered = [
        row for row in source_records
        if isinstance(row, dict) and row.get("id") == source_id
    ]
    if len(registered) != 1:
        raise PublicationApprovalError(
            f"Source ID {source_id!r} must resolve to exactly one registered source."
        )

    if not isinstance(identity_state, dict) or identity_state.get("format") != "civiccal.identity-state.v1":
        raise PublicationApprovalError("Identity state must use civiccal.identity-state.v1.")
    events = identity_state.get("events")
    if not isinstance(events, dict):
        raise PublicationApprovalError("Identity state events must be an object.")

    records_by_id = {}
    seen_ids = set()
    for identity_key, record in events.items():
        if not isinstance(record, dict):
            raise PublicationApprovalError(f"Identity record {identity_key!r} must be an object.")
        stored_id = record.get("event_id")
        stored_source = record.get("source_id")
        if not isinstance(stored_id, str) or not stored_id.strip():
            raise PublicationApprovalError(f"Identity record {identity_key!r} has no valid event_id.")
        if stored_id in seen_ids:
            raise PublicationApprovalError(f"Identity state contains duplicate event ID {stored_id!r}.")
        seen_ids.add(stored_id)
        if not isinstance(stored_source, str) or not stored_source.strip():
            raise PublicationApprovalError(f"Identity record {stored_id!r} has no valid source_id.")
        records_by_id[stored_id] = record
    if event_id not in records_by_id:
        raise PublicationApprovalError(f"Event ID {event_id!r} must resolve to exactly one stored event.")
    if records_by_id[event_id]["source_id"] != source_id:
        raise PublicationApprovalError(
            f"Event {event_id!r} belongs to source {records_by_id[event_id]['source_id']!r}, not {source_id!r}."
        )

    if not isinstance(manifest, dict) or manifest.get("format") != "civiccal.publication-manifest.v1":
        raise PublicationApprovalError("Publication manifest must use civiccal.publication-manifest.v1.")
    approved = manifest.get("approved_event_ids")
    if not isinstance(approved, list) or any(not isinstance(item, str) or not item.strip() for item in approved):
        raise PublicationApprovalError("approved_event_ids must be an array of non-empty event IDs.")
    if len(set(approved)) != len(approved):
        raise PublicationApprovalError("Publication manifest contains duplicate event IDs.")
    for approved_id in approved:
        approved_record = records_by_id.get(approved_id)
        if approved_record is None:
            raise PublicationApprovalError(
                f"Already-approved event ID {approved_id!r} is missing from identity state."
            )
        approved_source = approved_record["source_id"]
        registered_source_count = sum(
            1 for row in source_records
            if isinstance(row, dict) and row.get("id") == approved_source
        )
        if registered_source_count != 1:
            raise PublicationApprovalError(
                f"Approved event {approved_id!r} source {approved_source!r} "
                "must resolve to exactly one registered source."
            )

    updated = deepcopy(manifest)
    was_approved = event_id in approved
    if action == "approve" and not was_approved:
        updated["approved_event_ids"].append(event_id)
    elif action == "revoke" and was_approved:
        updated["approved_event_ids"] = [item for item in approved if item != event_id]

    now_approved = event_id in updated["approved_event_ids"]
    return updated, {
        "format": "civiccal.publication-action.v1",
        "action": action,
        "source_id": source_id,
        "event_id": event_id,
        "previously_approved": was_approved,
        "currently_approved": now_approved,
        "changed": was_approved != now_approved,
        "approved_event_count": len(updated["approved_event_ids"]),
        "manifest": "updated" if was_approved != now_approved else "unchanged",
    }


def _atomic_write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--identity-state", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--action", required=True, choices=["approve", "revoke"])
    args = parser.parse_args()

    try:
        if args.manifest.resolve() in {args.registry.resolve(), args.identity_state.resolve()}:
            raise PublicationApprovalError("Manifest path must be separate from registry and identity state.")
        registry = _load_object(args.registry, "source registry")
        state = _load_object(args.identity_state, "identity state")
        manifest = _load_object(args.manifest, "publication manifest")
        updated, summary = update_publication(
            registry, state, manifest, args.source_id, args.event_id, args.action
        )
        if summary["changed"]:
            _atomic_write_json(args.manifest, updated)
        sys.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
        return 0
    except (PublicationApprovalError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
