#!/usr/bin/env python3
"""Validate a capture manifest before asserting source snapshot completeness.

This offline gate attaches a conservative snapshot assertion to a normalized
event document. It never fetches pages or guesses that a listing is complete.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICIES = ROOT / "data" / "source-completeness.json"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SnapshotError(Exception):
    """Invalid manifest, policy, or normalized input."""


def _read_json(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"Cannot read {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise SnapshotError(f"{label} must be a JSON object.")
    return value


def _profile(policies: dict, source_id: str) -> dict:
    if policies.get("format") != "civiccal.source-completeness-policies.v1":
        raise SnapshotError("Unsupported source-completeness policy format.")
    matches = [p for p in policies.get("profiles", [])
               if isinstance(p, dict) and p.get("source_id") == source_id]
    if len(matches) != 1:
        raise SnapshotError(f"Expected exactly one completeness policy for {source_id!r}; found {len(matches)}.")
    return matches[0]


def validate_manifest(manifest: dict, profile: dict) -> dict:
    if manifest.get("format") != "civiccal.snapshot-manifest.v1":
        raise SnapshotError("Manifest must use civiccal.snapshot-manifest.v1.")
    source_id = manifest.get("source_id")
    if not isinstance(source_id, str) or source_id != profile.get("source_id"):
        raise SnapshotError("Manifest source_id does not match its completeness policy.")

    blockers: list[str] = []
    if profile.get("allow_complete_snapshot") is not True:
        blockers.append(str(profile.get("reason_disabled") or "Source policy does not permit completeness assertions."))

    pagination = manifest.get("pagination")
    if not isinstance(pagination, dict):
        pagination = {}
        blockers.append("Pagination evidence is missing.")
    strategy = pagination.get("strategy")
    if strategy != profile.get("pagination_strategy"):
        blockers.append("Pagination strategy does not match the source policy.")
    pages = manifest.get("pages")
    if not isinstance(pages, list) or not pages:
        pages = []
        blockers.append("No captured pages were supplied.")

    expected = pagination.get("expected_page_count")
    observed = pagination.get("observed_page_count")
    if not isinstance(expected, int) or expected < 1:
        blockers.append("expected_page_count must be a positive integer.")
    if expected != len(pages) or observed != len(pages):
        blockers.append("Expected, observed, and supplied page counts do not agree.")
    if pagination.get("terminal_page_confirmed") is not True:
        blockers.append("The terminal page has not been explicitly confirmed.")
    pending = pagination.get("pending_next_urls", [])
    if not isinstance(pending, list) or pending:
        blockers.append("One or more next-page URLs remain unprocessed.")

    required_roles = profile.get("required_page_roles", [])
    roles = set()
    page_urls = set()
    discovered_detail_ids: set[str] = set()
    parsed_detail_ids: set[str] = set()
    event_ids: set[str] = set()
    for index, page in enumerate(pages):
        if not isinstance(page, dict):
            blockers.append(f"Page {index + 1} is not an object.")
            continue
        role = page.get("role")
        roles.add(role)
        url = page.get("url")
        if not isinstance(url, str) or not url.startswith("https://"):
            blockers.append(f"Page {index + 1} has no HTTPS URL.")
        elif url in page_urls:
            blockers.append(f"Page {index + 1} duplicates a page URL.")
        else:
            page_urls.add(url)
        if page.get("capture_outcome") != "captured" or page.get("http_status") != 200:
            blockers.append(f"Page {index + 1} was not captured successfully with HTTP 200.")
        if page.get("parse_status") != "success":
            blockers.append(f"Page {index + 1} was not parsed successfully.")
        if not isinstance(page.get("content_sha256"), str) or not SHA256.fullmatch(page["content_sha256"]):
            blockers.append(f"Page {index + 1} has no valid SHA-256 payload hash.")
        ids = page.get("source_event_ids", [])
        if not isinstance(ids, list) or any(not isinstance(x, str) or not x.strip() for x in ids):
            blockers.append(f"Page {index + 1} has invalid source_event_ids.")
            ids = []
        event_ids.update(ids)
        discovered = page.get("discovered_detail_ids", [])
        if not isinstance(discovered, list) or any(not isinstance(x, str) or not x.strip() for x in discovered):
            blockers.append(f"Page {index + 1} has invalid discovered_detail_ids.")
            discovered = []
        discovered_detail_ids.update(discovered)
        if role == "detail":
            parsed_detail_ids.update(ids)

    missing_roles = set(required_roles) - roles
    if missing_roles:
        blockers.append("Required page roles are missing: " + ", ".join(sorted(missing_roles)) + ".")

    if profile.get("require_detail_link_reconciliation") is True:
        if discovered_detail_ids != parsed_detail_ids:
            missing = sorted(discovered_detail_ids - parsed_detail_ids)
            unexpected = sorted(parsed_detail_ids - discovered_detail_ids)
            if missing:
                blockers.append("Unparsed linked detail IDs: " + ", ".join(missing[:20]) + ".")
            if unexpected:
                blockers.append("Detail pages contain IDs not present in listing pages: " + ", ".join(unexpected[:20]) + ".")

    empty_confirmed = manifest.get("empty_snapshot_confirmed") is True
    if not event_ids and not empty_confirmed:
        blockers.append("No event IDs were observed; an explicit empty-snapshot confirmation is required.")

    completeness = "complete" if not blockers else "partial"
    if not pages or profile.get("allow_complete_snapshot") is not True:
        completeness = "unknown"

    evidence_parts = [
        f"profile={profile.get('profile_id')}",
        f"scope={profile.get('scope')}",
        f"pages={len(pages)}/{expected if isinstance(expected, int) else 'unspecified'}",
        f"pagination={strategy}",
    ]
    if profile.get("require_detail_link_reconciliation"):
        evidence_parts.append(f"details={len(parsed_detail_ids)}/{len(discovered_detail_ids)}")
    if blockers:
        evidence_parts.append("blockers=" + " | ".join(blockers))
    return {
        "completeness": completeness,
        "evidence": "; ".join(evidence_parts),
        "empty_snapshot_confirmed": empty_confirmed,
        "profile_id": profile.get("profile_id"),
        "scope": profile.get("scope"),
        "blockers": blockers,
    }


def attach_snapshot(normalized: dict, manifest: dict, policies: dict) -> dict:
    if normalized.get("format") != "civiccal.normalized-events.v1":
        raise SnapshotError("Input must use civiccal.normalized-events.v1.")
    source_id = normalized.get("source_id")
    if manifest.get("source_id") != source_id:
        raise SnapshotError("Normalized document and manifest source_id do not match.")
    profile = _profile(policies, source_id)
    result = copy.deepcopy(normalized)
    result["snapshot"] = validate_manifest(manifest, profile)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("normalized", type=Path, help="Normalized event document")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--policies", type=Path, default=DEFAULT_POLICIES)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        normalized = _read_json(args.normalized, "normalized event document")
        manifest = _read_json(args.manifest, "snapshot manifest")
        policies = _read_json(args.policies, "source-completeness policies")
        result = attach_snapshot(normalized, manifest, policies)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        snapshot = result["snapshot"]
        print(f"Snapshot completeness: {snapshot['completeness']}")
        for blocker in snapshot["blockers"]:
            print(f"- {blocker}")
        print(f"Output: {args.output}")
        return 0
    except (OSError, SnapshotError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
