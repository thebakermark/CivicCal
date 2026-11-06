#!/usr/bin/env python3
"""Ingest one previously archived capture into SQLite; never fetches or publishes."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    from .normalize_events import normalize_document
    from .parse_capture import (
        HandoffError, capture_summary, load_capture, parse_payload, select_adapter,
    )
    from .sqlite_storage import MigrationError, SQLiteIdentityStateStore
    from .track_event_identity import IdentityError
except ImportError:
    from normalize_events import normalize_document
    from parse_capture import (
        HandoffError, capture_summary, load_capture, parse_payload, select_adapter,
    )
    from sqlite_storage import MigrationError, SQLiteIdentityStateStore
    from track_event_identity import IdentityError


class IngestError(Exception):
    """Expected archived-capture ingestion error."""


def _source_from_database(database: Path, source_id: str) -> dict:
    try:
        with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as db:
            row = db.execute(
                "SELECT record_json FROM sources WHERE source_id=?", (source_id,)
            ).fetchone()
    except sqlite3.Error as exc:
        raise IngestError("Cannot read CivicCal source catalog from SQLite.") from exc
    if row is None:
        raise IngestError(f"Source {source_id!r} is not registered in the database.")
    try:
        source = json.loads(row[0])
    except json.JSONDecodeError as exc:
        raise IngestError("Stored source record is invalid.") from exc
    if not isinstance(source, dict):
        raise IngestError("Stored source record must be an object.")
    return source


def ingest_capture_sqlite(source_id: str, capture_metadata_path: Path,
                          database_path: Path, adapter: str = "auto") -> dict:
    try:
        source = _source_from_database(database_path, source_id)
        metadata, payload = load_capture(capture_metadata_path, source_id)
        selected_adapter = select_adapter(adapter, source.get("source_type"))
        page_url = metadata.get("final_url") or source.get("url")
        if not isinstance(page_url, str) or urlparse(page_url).scheme not in {"http", "https"}:
            raise IngestError("Capture has no usable HTTP(S) source page URL.")
        parser_output = parse_payload(payload, selected_adapter, source_id, page_url)
        parse_document = {
            "format": "civiccal.parse-result.v1",
            "source_id": source_id,
            "capture": capture_summary(metadata, capture_metadata_path, page_url),
            "parser_output": parser_output,
        }
        normalized = normalize_document(parse_document)
        observed_at = metadata.get("captured_at")
        if not isinstance(observed_at, str) or not observed_at.strip():
            raise IngestError("Capture metadata has no captured_at timestamp.")
        identity_result = SQLiteIdentityStateStore(database_path).ingest_normalized(
            normalized, observed_at=observed_at
        )
        return {
            "format": "civiccal.ingest-result.v1",
            "source_id": source_id,
            "adapter": selected_adapter,
            "capture_metadata": str(capture_metadata_path),
            "content_sha256": metadata.get("content_sha256"),
            "parser_event_count": parser_output.get("event_count", 0),
            "normalized_event_count": normalized.get("event_count", 0),
            "review_flagged_event_count": normalized.get("summary", {}).get("events_with_review_flags", 0),
            "new_events": identity_result.get("new_events", 0),
            "new_revisions": identity_result.get("new_revisions", 0),
            "unchanged_events": identity_result.get("unchanged_events", 0),
            "unkeyed_count": identity_result.get("unkeyed_count", 0),
            "identity_conflict_count": len(identity_result.get("identity_conflicts", [])),
            "already_processed": identity_result.get("already_processed", False),
            "database_file": str(database_path),
            "publication": "not_published; approval table remains separate",
            "network_fetch_performed": False,
            "parser_warnings": parser_output.get("warnings", []),
            "normalized_summary": normalized.get("summary", {}),
        }
    except (HandoffError, IdentityError, MigrationError, OSError, ValueError, sqlite3.Error) as exc:
        raise IngestError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--capture-metadata", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--adapter", default="auto",
                        choices=["auto", "ics", "jsonld", "mokena_park", "village"])
    parser.add_argument("--report", type=Path, help="Optional JSON ingestion report path")
    args = parser.parse_args()
    try:
        result = ingest_capture_sqlite(
            args.source_id, args.capture_metadata, args.database, args.adapter
        )
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        print(
            f"Ingested {result['parser_event_count']} source record(s): "
            f"{result['new_events']} new tracked event(s), "
            f"{result['new_revisions']} revision(s), "
            f"{result['unkeyed_count']} retained for identity review.",
            file=sys.stderr,
        )
        return 0
    except IngestError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
