#!/usr/bin/env python3
"""Explicit operator CLI to approve or revoke one source-owned event."""
from __future__ import annotations

import argparse
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ApprovalError(ValueError):
    """Invalid or unauthorized publication approval operation."""


def set_approval(database: Path, source_id: str, event_id: str, action: str,
                 actor: str, reason: str | None = None) -> dict:
    if action not in {"approve", "revoke"}:
        raise ApprovalError("action must be approve or revoke")
    if not source_id.strip() or not event_id.strip() or not actor.strip():
        raise ApprovalError("source_id, event_id, and actor must be non-empty")
    connection = sqlite3.connect(database, timeout=30)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        event = connection.execute(
            "SELECT source_id FROM source_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if event is None:
            raise ApprovalError(f"Event {event_id!r} does not exist")
        if event[0] != source_id:
            raise ApprovalError("Event does not belong to the supplied source")
        desired = 1 if action == "approve" else 0
        current = connection.execute(
            "SELECT source_id, approved FROM publication_approvals WHERE event_id=?",
            (event_id,),
        ).fetchone()
        if current and current[0] != source_id:
            raise ApprovalError("Existing approval has conflicting source ownership")
        if current and current[1] == desired:
            connection.commit()
            return {"changed": False, "action": action, "event_id": event_id,
                    "source_id": source_id}
        if current:
            connection.execute(
                "UPDATE publication_approvals SET approved=?, imported_from=? WHERE event_id=?",
                (desired, "operator_cli", event_id),
            )
        else:
            connection.execute(
                "INSERT INTO publication_approvals VALUES(?,?,?,?)",
                (event_id, source_id, desired, "operator_cli"),
            )
        acted_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        action_id = "act_" + uuid.uuid4().hex
        connection.execute(
            "INSERT INTO publication_approval_actions VALUES(?,?,?,?,?,?,?)",
            (action_id, event_id, source_id, action, acted_at, actor.strip(), reason),
        )
        connection.commit()
        return {"changed": True, "action": action, "event_id": event_id,
                "source_id": source_id, "action_id": action_id, "acted_at": acted_at}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--action", required=True, choices=["approve", "revoke"])
    parser.add_argument("--actor", required=True, help="Operator identity for the audit record")
    parser.add_argument("--reason")
    args = parser.parse_args()
    try:
        result = set_approval(args.database, args.source_id, args.event_id,
                              args.action, args.actor, args.reason)
    except (ApprovalError, OSError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
