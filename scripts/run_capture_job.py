#!/usr/bin/env python3
"""Run one operator-requested, policy-gated ICS capture and write a report.

This is a job runner, not an HTTP service, scheduler, or polling daemon. It
reuses CivicCal's existing capture coordinator and never edits source policy.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.capture_ics_source import (
    ICSCoordinatorError,
    coordinate_ics_capture,
)
from scripts.capture_source import CaptureError, load_source
from scripts.normalize_events import NormalizationError
from scripts.validate_snapshot import SnapshotError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = Path("/srv/civiccal/data/registry/sources.json")
DEFAULT_POLICIES = ROOT / "data" / "source-completeness.json"
DEFAULT_ARCHIVE = Path("/srv/civiccal/data/captures")
DEFAULT_REPORTS = Path("/srv/civiccal/data/reports")


def safe_source_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
        raise argparse.ArgumentTypeError("source ID must contain lowercase letters, digits, and hyphens only")
    return value


def run_job(source_id: str, *, registry: Path, policies: Path,
            archive_dir: Path, reports_dir: Path, timeout: int = 20,
            empty_snapshot_confirmed: bool = False) -> tuple[Path, dict]:
    """Run exactly one capture; return the report path and normalized result."""
    if not 1 <= timeout <= 120:
        raise ValueError("timeout must be between 1 and 120 seconds")

    # Load the source through the same hard authorization gates as the CLI.
    # This reads the registry; it does not mutate any registry fields.
    source = load_source(registry, source_id)
    result = coordinate_ics_capture(
        source, policies, archive_dir, timeout=timeout,
        empty_snapshot_confirmed=empty_snapshot_confirmed,
    )

    reports_dir.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.now(timezone.utc)
    stamp = captured_at.strftime("%Y%m%dT%H%M%SZ")
    report_path = reports_dir / f"{source_id}-{stamp}.json"
    report = {
        "format": "civiccal.capture-job-report.v1",
        "job": {
            "source_id": source_id,
            "started_or_completed_at": captured_at.isoformat(),
            "outcome": "success",
            "automatic_polling_enabled": False,
            "published": False,
            "source_registry_modified": False,
        },
        "capture": result,
    }
    temporary_path = report_path.with_suffix(".json.tmp")
    temporary_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(report_path)
    return report_path, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True, type=safe_source_id)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument(
        "--confirm-empty-snapshot", action="store_true",
        help="Operator attestation for a genuinely empty feed; cannot override source policy.",
    )
    args = parser.parse_args()
    try:
        report_path, result = run_job(
            args.source_id, registry=args.registry, policies=args.policies,
            archive_dir=args.archive_dir, reports_dir=args.reports_dir,
            timeout=args.timeout,
            empty_snapshot_confirmed=args.confirm_empty_snapshot,
        )
        summary = result.get("summary", {})
        print(f"Capture succeeded: {args.source_id}")
        print(f"Events: {result.get('event_count', 0)}")
        print(f"Snapshot completeness: {result.get('snapshot', {}).get('completeness', 'unknown')}")
        print(f"Parser warnings: {summary.get('parser_warning_count', 0)}")
        print(f"Report: {report_path}")
        return 0
    except (CaptureError, ICSCoordinatorError, NormalizationError, SnapshotError,
            OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"CAPTURE FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
