#!/usr/bin/env python3
"""Create a consistent SQLite online backup and verify it before publication."""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


def verify_database(path: Path) -> None:
    with sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"SQLite integrity check failed: {integrity}")
        violations = db.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise ValueError(f"SQLite foreign-key check failed: {len(violations)} violation(s)")
        version = db.execute(
            "SELECT value FROM schema_meta WHERE key='schema_version'"
        ).fetchone()
        if version is None or version[0] != "1":
            raise ValueError("Unsupported CivicCal SQLite schema version")


def create_backup(database: Path, destination: Path) -> None:
    if not database.is_file():
        raise ValueError("Source database does not exist")
    if destination.exists():
        raise ValueError("Refusing to overwrite an existing backup")
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp",
                                     dir=destination.parent)
    os.close(fd)
    temp_path = Path(temporary)
    try:
        with sqlite3.connect(f"file:{database.resolve()}?mode=ro", uri=True) as source:
            with sqlite3.connect(temp_path) as target:
                source.backup(target)
                target.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                target.commit()
        verify_database(temp_path)
        with temp_path.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temp_path, destination)
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-only", action="store_true",
                        help="Verify an existing database or backup without changing it")
    args = parser.parse_args()
    try:
        if args.verify_only:
            if args.output is not None:
                parser.error("--output cannot be used with --verify-only")
            verify_database(args.database)
            print(f"Verified CivicCal SQLite database: {args.database}")
        else:
            if args.output is None:
                parser.error("--output is required unless --verify-only is used")
            create_backup(args.database, args.output)
            verify_database(args.output)
            print(f"Verified CivicCal SQLite backup: {args.output}")
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
