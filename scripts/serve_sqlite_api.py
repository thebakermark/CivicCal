#!/usr/bin/env python3
"""Serve CivicCal's SQLite-backed read-only API and per-source ICS feeds."""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

try:
    from .serve_api import OPENAPI
    from .query_events import QueryError
    from .publish_ics import FeedError
    from .sqlite_queries import SQLiteReadError, build_source_calendar, query_events_db
except ImportError:
    from serve_api import OPENAPI
    from query_events import QueryError
    from publish_ics import FeedError
    from sqlite_queries import SQLiteReadError, build_source_calendar, query_events_db


def make_handler(database_path: Path):
    class SQLiteCivicCalHandler(BaseHTTPRequestHandler):
        server_version = "CivicCal/1.0"
        sys_version = ""

        def log_message(self, format_string, *args):
            return

        def _send(self, status: int, body: bytes, content_type: str,
                  etag: str | None = None, last_modified: str | None = None):
            if etag and self.headers.get("If-None-Match") in {etag, "*"}:
                self.send_response(304)
                self.send_header("ETag", etag)
                if last_modified:
                    self.send_header("Last-Modified", last_modified)
                self.send_header("Cache-Control", "private, max-age=60")
                self.end_headers()
                return
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "private, max-age=60")
            if etag:
                self.send_header("ETag", etag)
            if last_modified:
                self.send_header("Last-Modified", last_modified)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, status: int, value: dict):
            body = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
            etag = '"' + hashlib.sha256(body).hexdigest() + '"'
            self._send(status, body, "application/json; charset=utf-8", etag)

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == "/health":
                self._json(200, {"status": "ok", "mode": "read-only", "storage": "sqlite"})
                return
            if parsed.path in {"/openapi.json", "/api/v1/openapi.json"}:
                self._json(200, OPENAPI)
                return
            if parsed.path == "/api/v1/events":
                try:
                    params = parse_qs(parsed.query, keep_blank_values=False)
                    allowed = {"start_date", "end_date", "source_id", "category", "q", "limit", "offset"}
                    unknown = sorted(set(params) - allowed)
                    if unknown:
                        raise QueryError("Unsupported query parameter: " + ", ".join(unknown))
                    if any(len(values) != 1 for values in params.values()):
                        raise QueryError("Each query parameter may be supplied only once.")
                    values = {key: items[0] for key, items in params.items()}
                    try:
                        limit = int(values.get("limit", "50"))
                        offset = int(values.get("offset", "0"))
                    except ValueError as exc:
                        raise QueryError("limit and offset must be integers.") from exc
                    result = query_events_db(
                        database_path,
                        start_date=values.get("start_date"),
                        end_date=values.get("end_date"),
                        source_id=values.get("source_id"),
                        category=values.get("category"),
                        q=values.get("q"),
                        limit=limit,
                        offset=offset,
                    )
                    body = (json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
                    etag = '"' + hashlib.sha256(body).hexdigest() + '"'
                    self._send(200, body, "application/json; charset=utf-8", etag)
                except QueryError as exc:
                    self._json(400, {"error": "invalid_request", "message": str(exc)})
                except (SQLiteReadError, OSError):
                    self._json(503, {"error": "service_unavailable"})
                return

            prefix = "/calendars/sources/"
            suffix = ".ics"
            if parsed.path.startswith(prefix) and parsed.path.endswith(suffix):
                source_id = unquote(parsed.path[len(prefix):-len(suffix)])
                if not source_id or "/" in source_id:
                    self._json(404, {"error": "not_found"})
                    return
                try:
                    rendered, _, modified = build_source_calendar(database_path, source_id)
                    body = rendered.encode("utf-8")
                    etag = '"' + hashlib.sha256(body).hexdigest() + '"'
                    last_modified = None
                    if modified:
                        try:
                            parsed_time = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                            if parsed_time.tzinfo is not None:
                                last_modified = format_datetime(parsed_time.astimezone(timezone.utc), usegmt=True)
                        except ValueError:
                            last_modified = None
                    self._send(200, body, "text/calendar; charset=utf-8", etag, last_modified)
                except KeyError:
                    self._json(404, {"error": "source_not_found"})
                except FeedError:
                    self._json(503, {"error": "service_unavailable"})
                except (SQLiteReadError, OSError):
                    self._json(503, {"error": "service_unavailable"})
                return
            self._json(404, {"error": "not_found"})

        def do_POST(self):
            self._json(405, {"error": "method_not_allowed"})

        def do_PUT(self):
            self._json(405, {"error": "method_not_allowed"})

        def do_DELETE(self):
            self._json(405, {"error": "method_not_allowed"})

    return SQLiteCivicCalHandler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Migrated CivicCal SQLite database")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback address only")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        address = ipaddress.ip_address(args.host)
        if not address.is_loopback:
            raise ValueError("CivicCal API binds to loopback only; remote hosting is not enabled.")
        if not 1 <= args.port <= 65535:
            raise ValueError("port must be between 1 and 65535.")
        database = Path(args.database)
        if not database.is_file():
            raise ValueError("SQLite database file does not exist.")
        # Open once at startup so a missing or invalid schema fails closed.
        from sqlite3 import connect
        with connect(f"file:{database.resolve()}?mode=ro", uri=True) as db:
            version = db.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
            if version is None or version[0] != "1":
                raise ValueError("Unsupported CivicCal SQLite schema version.")
        server = ThreadingHTTPServer((str(address), args.port), make_handler(database))
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"CivicCal SQLite API listening on http://{args.host}:{args.port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
