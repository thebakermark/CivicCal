#!/usr/bin/env python3
"""Serve CivicCal's approved JSON and iCalendar projections on loopback only."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

try:
    from .publish_ics import FeedError, build_calendar
    from .query_events import QueryError, query_events
except ImportError:  # direct script execution
    from publish_ics import FeedError, build_calendar
    from query_events import QueryError, query_events


OPENAPI = {
    "openapi": "3.1.1",
    "info": {"title": "CivicCal Read-only API", "version": "1.0.0"},
    "paths": {
        "/health": {"get": {"summary": "Service health"}},
        "/api/v1/openapi.json": {"get": {"summary": "OpenAPI description"}},
        "/api/v1/events": {
            "get": {
                "summary": "List explicitly approved public events",
                "parameters": [
                    {"name": name, "in": "query", "schema": schema}
                    for name, schema in [
                        ("start_date", {"type": "string", "format": "date"}),
                        ("end_date", {"type": "string", "format": "date"}),
                        ("source_id", {"type": "string"}),
                        ("category", {"type": "string"}),
                        ("q", {"type": "string"}),
                        ("limit", {"type": "integer", "minimum": 1, "maximum": 100, "default": 50}),
                        ("offset", {"type": "integer", "minimum": 0, "default": 0}),
                    ]
                ],
                "responses": {"200": {"description": "Paginated approved event results"}},
            }
        },
        "/calendars/sources/{source_id}.ics": {
            "get": {"summary": "Subscribe to one registered source's approved events"}
        },
    },
}


class ServiceInputError(Exception):
    pass


class DataUnavailable(Exception):
    pass


def _load_documents(state_path: Path, manifest_path: Path) -> tuple[dict, dict]:
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataUnavailable("CivicCal data files are unavailable or invalid.") from exc
    return state, manifest


def _load_registry(registry_path: Path) -> dict:
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataUnavailable("CivicCal source registry is unavailable or invalid.") from exc
    if not isinstance(registry, dict) or not isinstance(registry.get("source_records"), list):
        raise DataUnavailable("CivicCal source registry has no valid source_records array.")
    seen = set()
    for record in registry["source_records"]:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str) or not record["id"].strip():
            raise DataUnavailable("CivicCal source registry contains an invalid source record.")
        source_id = record["id"]
        if source_id in seen:
            raise DataUnavailable("CivicCal source registry contains duplicate source IDs.")
        seen.add(source_id)
    return registry


def _last_modified(state: dict, manifest: dict, source_id: str | None = None) -> str | None:
    approved = manifest.get("approved_event_ids", [])
    approved_set = {item for item in approved if isinstance(item, str)} if isinstance(approved, list) else set()
    timestamps = []
    events = state.get("events", {}) if isinstance(state, dict) else {}
    if not isinstance(events, dict):
        return None
    for record in events.values():
        if not isinstance(record, dict) or record.get("event_id") not in approved_set:
            continue
        if source_id is not None and record.get("source_id") != source_id:
            continue
        revisions = record.get("revisions")
        if not isinstance(revisions, list) or not revisions or not isinstance(revisions[-1], dict):
            continue
        observed = revisions[-1].get("observed_at")
        if not isinstance(observed, str):
            continue
        try:
            parsed = datetime.fromisoformat(observed.replace("Z", "+00:00"))
            if parsed.tzinfo is not None:
                timestamps.append(parsed.astimezone(timezone.utc))
        except ValueError:
            continue
    return format_datetime(max(timestamps), usegmt=True) if timestamps else None


def make_handler(state_path: Path, manifest_path: Path, registry_path: Path | None = None):
    class CivicCalHandler(BaseHTTPRequestHandler):
        server_version = "CivicCal/0.1"
        sys_version = ""

        def log_message(self, format_string, *args):
            # Avoid logging user-supplied search text from query strings.
            return

        def _send(self, status: int, body: bytes, content_type: str,
                  etag: str | None = None, last_modified: str | None = None):
            if etag and self.headers.get("If-None-Match") in {etag, "*"}:
                self.send_response(304)
                self.send_header("ETag", etag)
                if last_modified:
                    self.send_header("Last-Modified", last_modified)
                self.send_header("Cache-Control", "public, max-age=60")
                self.end_headers()
                return
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            if etag:
                self.send_header("ETag", etag)
            if last_modified:
                self.send_header("Last-Modified", last_modified)
            self.send_header("Cache-Control", "public, max-age=60")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, value: dict, etag_source: bytes | None = None,
                  last_modified: str | None = None):
            body = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            digest = etag_source if etag_source is not None else body
            etag = '"' + hashlib.sha256(digest).hexdigest() + '"'
            self._send(status, body, "application/json; charset=utf-8", etag, last_modified)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == "/health":
                self._json(200, {"status": "ok", "mode": "read-only", "storage": "file"})
                return
            if parsed.path in {"/openapi.json", "/api/v1/openapi.json"}:
                self._json(200, OPENAPI)
                return
            source_match = re.fullmatch(r"/calendars/sources/([^/]+)\.ics", parsed.path)
            if parsed.path != "/api/v1/events" and source_match is None:
                self._json(404, {"error": "not_found"})
                return
            try:
                state, manifest = _load_documents(state_path, manifest_path)
                if source_match is not None:
                    if registry_path is None:
                        raise DataUnavailable("Source-specific relays require a source registry.")
                    registry = _load_registry(registry_path)
                    source_id = unquote(source_match.group(1))
                    sources = {record["id"]: record for record in registry["source_records"]}
                    if source_id not in sources:
                        self._json(404, {"error": "source_not_found"})
                        return
                    approved = manifest.get("approved_event_ids")
                    if (not isinstance(approved, list)
                            or any(not isinstance(item, str) or not item for item in approved)):
                        raise FeedError("approved_event_ids must be an array of non-empty event IDs.")
                    if len(set(approved)) != len(approved):
                        raise FeedError("Publication manifest contains duplicate event IDs.")
                    records = state.get("events") if isinstance(state, dict) else None
                    if not isinstance(records, dict):
                        raise FeedError("Identity state events must be an object.")
                    records_by_id = {}
                    for record in records.values():
                        if not isinstance(record, dict) or not isinstance(record.get("event_id"), str):
                            continue
                        event_id = record["event_id"]
                        if event_id in records_by_id:
                            raise FeedError("Identity state contains duplicate event IDs.")
                        records_by_id[event_id] = record
                    missing = [event_id for event_id in approved if event_id not in records_by_id]
                    if missing:
                        raise FeedError("Approved event IDs are missing from identity state.")
                    approved_for_source = [
                        event_id for event_id in approved
                        if records_by_id[event_id].get("source_id") == source_id
                    ]
                    source_manifest = dict(manifest)
                    source_manifest["approved_event_ids"] = approved_for_source
                    source_manifest["calendar_name"] = sources[source_id].get("name") or source_id
                    source_state = dict(state)
                    approved_set = set(approved_for_source)
                    source_state["events"] = {
                        key: record for key, record in records.items()
                        if isinstance(record, dict) and record.get("event_id") in approved_set
                    }
                    body_text, _ = build_calendar(source_state, source_manifest)
                    body = body_text.encode("utf-8")
                    etag = '"' + hashlib.sha256(body).hexdigest() + '"'
                    last_modified = _last_modified(state, manifest, source_id)
                    self._send(200, body, "text/calendar; charset=utf-8", etag, last_modified)
                    return

                params = parse_qs(parsed.query, keep_blank_values=False, strict_parsing=False)
                allowed = {"start_date", "end_date", "source_id", "category", "q", "limit", "offset"}
                unknown = sorted(set(params) - allowed)
                if unknown:
                    raise ServiceInputError("Unsupported query parameter: " + ", ".join(unknown))
                if any(len(values) != 1 for values in params.values()):
                    raise ServiceInputError("Each query parameter may be supplied only once.")
                values = {key: items[0] for key, items in params.items()}
                try:
                    limit = int(values.get("limit", "50"))
                    offset = int(values.get("offset", "0"))
                except ValueError as exc:
                    raise ServiceInputError("limit and offset must be integers.") from exc
                result = query_events(
                    state, manifest,
                    start_date=values.get("start_date"),
                    end_date=values.get("end_date"),
                    source_id=values.get("source_id"),
                    category=values.get("category"),
                    q=values.get("q"),
                    limit=limit,
                    offset=offset,
                )
                self._json(200, result, last_modified=_last_modified(state, manifest, values.get("source_id")))
            except FeedError:
                # Invalid stored publication/identity data is a server-side
                # integrity failure, not a malformed client request.
                self._json(503, {"error": "service_unavailable"})
            except (QueryError, ServiceInputError) as exc:
                self._json(400, {"error": "invalid_request", "message": str(exc)})
            except DataUnavailable:
                self._json(503, {"error": "service_unavailable"})
            except Exception:
                self._json(500, {"error": "internal_error"})

        def do_POST(self):
            self._json(405, {"error": "method_not_allowed"})

        def do_PUT(self):
            self._json(405, {"error": "method_not_allowed"})

        def do_DELETE(self):
            self._json(405, {"error": "method_not_allowed"})

    return CivicCalHandler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, help="Identity-state JSON path")
    parser.add_argument("--manifest", required=True, help="Publication approval manifest JSON path")
    parser.add_argument("--registry", required=True, help="Source registry JSON path")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback address only")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        address = ipaddress.ip_address(args.host)
        if not address.is_loopback:
            raise ValueError("CivicCal API binds to loopback only; remote hosting is not enabled.")
        if not 1 <= args.port <= 65535:
            raise ValueError("port must be between 1 and 65535.")
        state_path, manifest_path, registry_path = Path(args.state), Path(args.manifest), Path(args.registry)
        _load_documents(state_path, manifest_path)
        _load_registry(registry_path)
        server = ThreadingHTTPServer((args.host, args.port), make_handler(state_path, manifest_path, registry_path))
        print(f"CivicCal read-only API listening on http://{args.host}:{args.port}")
        server.serve_forever()
        return 0
    except (ValueError, OSError, ServiceInputError, DataUnavailable) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
