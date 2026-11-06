#!/usr/bin/env python3
"""Explicit, offline JSON-to-SQLite migration. Never fetches or publishes."""
from __future__ import annotations

import argparse
import json
import sys

try:
    from .sqlite_storage import MigrationError, migrate_files
except ImportError:
    from sqlite_storage import MigrationError, migrate_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--manifest", required=True)
    args = parser.parse_args()
    try:
        counts = migrate_files(args.database, args.registry, args.state, args.manifest)
    except (MigrationError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "format": "civiccal.sqlite-migration-result.v1",
        "database": args.database,
        "counts": counts,
        "capture_performed": False,
        "publication_performed": False,
        "source_authorization_changed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
