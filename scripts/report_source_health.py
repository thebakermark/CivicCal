#!/usr/bin/env python3
"""Report CivicCal source policy and archived-capture health without network access."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "sources.json"
DEFAULT_ARCHIVE = ROOT / "data" / "captures"


class ReportError(Exception):
    pass


def _read_registry(path: Path) -> list[dict]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReportError(f"Cannot read source registry: {exc}") from exc
    rows = value.get("source_records") if isinstance(value, dict) else None
    if not isinstance(rows, list):
        raise ReportError("Source registry must contain a source_records array.")
    if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in rows):
        raise ReportError("Every source record must be an object with a string id.")
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ReportError("Source registry contains duplicate source IDs.")
    return rows


def _capture_history(source_id: str, archive: Path) -> tuple[list[dict], list[str]]:
    folder = archive / source_id
    if not folder.exists():
        return [], []
    if not folder.is_dir():
        return [], [f"{source_id}: archive path is not a directory."]
    records: list[dict] = []
    warnings: list[str] = []
    for metadata_path in sorted(folder.glob("*.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"{source_id}: unreadable metadata file {metadata_path.name}: {exc}")
            continue
        if not isinstance(metadata, dict):
            warnings.append(f"{source_id}: metadata file {metadata_path.name} is not an object.")
            continue
        if metadata.get("source_id") != source_id:
            warnings.append(f"{source_id}: metadata source_id mismatch in {metadata_path.name}.")
            continue
        if metadata.get("format") != "civiccal.raw-capture.v1":
            warnings.append(f"{source_id}: unsupported metadata format in {metadata_path.name}.")
            continue
        outcome = metadata.get("outcome")
        payload_name = metadata.get("raw_payload_file")
        if outcome == "captured":
            if not isinstance(payload_name, str) or Path(payload_name).name != payload_name:
                warnings.append(f"{source_id}: unsafe or missing payload reference in {metadata_path.name}.")
            else:
                payload_path = folder / payload_name
                try:
                    body = payload_path.read_bytes()
                except OSError:
                    warnings.append(f"{source_id}: payload missing for {metadata_path.name}.")
                else:
                    actual = hashlib.sha256(body).hexdigest()
                    if actual != metadata.get("content_sha256"):
                        warnings.append(f"{source_id}: payload hash mismatch for {metadata_path.name}.")
        elif outcome == "not_modified":
            if payload_name is not None:
                warnings.append(f"{source_id}: 304 metadata unexpectedly references a payload.")
        else:
            warnings.append(f"{source_id}: unknown capture outcome in {metadata_path.name}.")
        records.append({
            "captured_at": metadata.get("captured_at"),
            "outcome": outcome,
            "http_status": metadata.get("http_status"),
            "content_type": metadata.get("content_type"),
            "content_length": metadata.get("content_length"),
            "content_sha256": metadata.get("content_sha256"),
            "page_role": metadata.get("page_role"),
            "metadata_file": metadata_path.name,
        })
    records.sort(key=lambda item: str(item.get("captured_at") or ""), reverse=True)
    return records, warnings


def build_report(registry_path: Path, archive_dir: Path) -> dict:
    sources = _read_registry(registry_path)
    report_sources = []
    warnings: list[str] = []
    for source in sorted(sources, key=lambda item: (str(item.get("organization_id", "")), item["id"])):
        history, source_warnings = _capture_history(source["id"], archive_dir)
        warnings.extend(source_warnings)
        latest = history[0] if history else None
        if source.get("consent_required") is True and source.get("consent_granted") is not True:
            policy_state = "consent_required"
        elif source.get("access_status") != "approved":
            policy_state = str(source.get("access_status") or "unclassified")
        elif source.get("terms_reviewed") is not True or source.get("robots_reviewed") is not True:
            policy_state = "review_incomplete"
        else:
            policy_state = "approved"
        report_sources.append({
            "source_id": source["id"],
            "organization_id": source.get("organization_id"),
            "name": source.get("name"),
            "source_type": source.get("source_type"),
            "policy_state": policy_state,
            "polling_enabled": source.get("polling_enabled") is True,
            "consent_required": source.get("consent_required") is True,
            "consent_granted": source.get("consent_granted") is True,
            "latest_capture": latest,
            "capture_count": len(history),
            "capture_history": history,
        })
    counts: dict[str, int] = {}
    for item in report_sources:
        counts[item["policy_state"]] = counts.get(item["policy_state"], 0) + 1
    return {
        "format": "civiccal.source-health-report.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "network_access": False,
        "summary": {
            "source_count": len(report_sources),
            "policy_state_counts": counts,
            "sources_with_captures": sum(1 for item in report_sources if item["capture_count"]),
            "sources_without_captures": sum(1 for item in report_sources if not item["capture_count"]),
            "polling_enabled_sources": sum(1 for item in report_sources if item["polling_enabled"]),
            "warning_count": len(warnings),
        },
        "sources": report_sources,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--archive-dir", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, help="Write JSON report to this path; stdout if omitted.")
    args = parser.parse_args()
    try:
        report = build_report(args.registry, args.archive_dir)
        rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0 if not report["warnings"] else 1
    except ReportError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
