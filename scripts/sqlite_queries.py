"""Read-only SQLite query path used by CivicCal's API and ICS relay."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .publish_ics import FeedError, build_calendar_records
from .query_events import QueryError, PUBLIC_EVENT_FIELDS, _parse_date


class SQLiteReadError(RuntimeError):
    """The persisted SQLite read model is unavailable or inconsistent."""


def _connect(database_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{Path(database_path).resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def query_events_db(database_path: str | Path, *, start_date: str | None = None,
                    end_date: str | None = None, source_id: str | None = None,
                    category: str | None = None, q: str | None = None,
                    limit: int = 50, offset: int = 0) -> dict:
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise QueryError("limit must be between 1 and 100.")
    if not isinstance(offset, int) or offset < 0:
        raise QueryError("offset must be zero or greater.")
    start_bound = _parse_date(start_date, "start_date")
    end_bound = _parse_date(end_date, "end_date")
    if start_bound and end_bound and end_bound < start_bound:
        raise QueryError("end_date cannot be earlier than start_date.")

    clauses = ["a.approved=1"]
    params: list[object] = []
    if source_id:
        clauses.append("e.source_id=?")
        params.append(source_id)
    if start_bound:
        clauses.append("date(substr(json_extract(e.current_event_json,'$.start.value'),1,10)) >= date(?)")
        params.append(start_bound.isoformat())
    if end_bound:
        clauses.append("date(substr(json_extract(e.current_event_json,'$.start.value'),1,10)) <= date(?)")
        params.append(end_bound.isoformat())
    category_value = category.casefold().strip() if isinstance(category, str) else ""
    if category_value:
        clauses.append("""EXISTS (
            SELECT 1 FROM json_each(e.current_event_json, '$.categories') c
            WHERE lower(CAST(c.value AS TEXT))=lower(?)
        )""")
        params.append(category_value)
    needle = q.casefold().strip() if isinstance(q, str) else ""
    if needle:
        clauses.append("""(
            lower(COALESCE(json_extract(e.current_event_json,'$.title'),'')) LIKE ?
            OR lower(COALESCE(json_extract(e.current_event_json,'$.description'),'')) LIKE ?
        )""")
        escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = "%" + escaped + "%"
        params.extend([pattern, pattern])

    where = " AND ".join(clauses)
    sql = f"""
        SELECT e.event_id, e.source_id, e.current_event_json,
               e.current_revision_number, e.lifecycle_status
        FROM source_events e
        JOIN publication_approvals a ON a.event_id=e.event_id
        WHERE {where}
        ORDER BY COALESCE(substr(json_extract(e.current_event_json,'$.start.value'),1,10),'9999-12-31'),
                 e.event_id
        LIMIT ? OFFSET ?
    """
    try:
        with _connect(database_path) as db:
            total = db.execute(
                f"""SELECT COUNT(*) FROM source_events e
                    JOIN publication_approvals a ON a.event_id=e.event_id
                    WHERE {where}""", params
            ).fetchone()[0]
            rows = db.execute(sql, [*params, limit, offset]).fetchall()
    except (sqlite3.Error, OSError) as exc:
        raise SQLiteReadError("SQLite event query failed") from exc

    output = []
    for row in rows:
        try:
            current = json.loads(row["current_event_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise SQLiteReadError("Stored event JSON is invalid") from exc
        if not isinstance(current, dict):
            raise SQLiteReadError("Stored event JSON must be an object")
        output.append({
            "event_id": row["event_id"],
            "revision": row["current_revision_number"],
            "source_id": row["source_id"],
            "lifecycle_status": row["lifecycle_status"] or current.get("status") or "unknown",
            "event": {field: current[field] for field in PUBLIC_EVENT_FIELDS if field in current},
        })
    next_offset = offset + limit if offset + limit < total else None
    return {
        "format": "civiccal.api-events.v1",
        "filters": {"start_date": start_date, "end_date": end_date,
                    "source_id": source_id, "category": category, "q": q},
        "pagination": {"total": total, "limit": limit, "offset": offset,
                       "next_offset": next_offset},
        "events": output,
    }


def build_source_calendar(database_path: str | Path, source_id: str) -> tuple[str, dict, str | None]:
    try:
        with _connect(database_path) as db:
            source = db.execute(
                "SELECT record_json FROM sources WHERE source_id=?", (source_id,)
            ).fetchone()
            if source is None:
                raise KeyError(source_id)
            source_record = json.loads(source["record_json"])
            if not isinstance(source_record, dict):
                raise SQLiteReadError("Stored source registry record is invalid")
            rows = db.execute(
                """SELECT e.event_id, e.source_id, e.current_event_json,
                          e.current_revision_number,
                          (SELECT r.observed_at FROM event_revisions r
                           WHERE r.event_id=e.event_id
                           ORDER BY r.revision_number DESC LIMIT 1) AS latest_observed_at
                   FROM source_events e
                   JOIN publication_approvals a ON a.event_id=e.event_id
                   WHERE e.source_id=? AND a.approved=1
                   ORDER BY e.event_id""",
                (source_id,),
            ).fetchall()
    except KeyError:
        raise
    except (sqlite3.Error, OSError, json.JSONDecodeError) as exc:
        raise SQLiteReadError("SQLite source calendar query failed") from exc

    records = {}
    timestamps = []
    for row in rows:
        try:
            current = json.loads(row["current_event_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise SQLiteReadError("Stored event JSON is invalid") from exc
        records[row["event_id"]] = {
            "event_id": row["event_id"], "source_id": row["source_id"],
            "current": current,
            "revisions": [{"revision": row["current_revision_number"],
                           "observed_at": row["latest_observed_at"]}],
        }
        if row["latest_observed_at"]:
            try:
                parsed = datetime.fromisoformat(row["latest_observed_at"].replace("Z", "+00:00"))
                if parsed.tzinfo is not None:
                    timestamps.append(parsed.astimezone(timezone.utc))
            except (TypeError, ValueError):
                continue
    approved = list(records)
    name = source_record.get("name") or source_id
    try:
        rendered, summary = build_calendar_records(records, approved, name)
    except FeedError:
        raise
    modified = max(timestamps).isoformat().replace("+00:00", "Z") if timestamps else None
    return rendered, summary, modified
