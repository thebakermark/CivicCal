#!/usr/bin/env python3
"""Validate CivicCal's source registry using only the Python standard library."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "sources.json"
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
SOURCE_TYPES = {"ics", "rss", "atom", "json_api", "html", "email"}
ACCESS_STATES = {"discovered", "review_required", "approved", "blocked", "retired"}
ORG_STATES = {
    "candidate",
    "organization_verification_required",
    "official_site_identified",
    "feed_verification_required",
    "research_required",
    "verified",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def valid_http_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main() -> int:
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {REGISTRY.relative_to(ROOT)}: {exc}")
        return 1

    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    organizations = data.get("organizations")
    sources = data.get("source_records")
    if not isinstance(organizations, list):
        errors.append("organizations must be an array")
        organizations = []
    if not isinstance(sources, list):
        errors.append("source_records must be an array")
        sources = []

    organization_ids: set[str] = set()
    for index, org in enumerate(organizations):
        prefix = f"organizations[{index}]"
        if not isinstance(org, dict):
            errors.append(f"{prefix} must be an object")
            continue
        org_id = org.get("id")
        if not valid_id(org_id):
            errors.append(f"{prefix}.id is missing or invalid")
        elif org_id in organization_ids:
            errors.append(f"duplicate organization id: {org_id}")
        else:
            organization_ids.add(org_id)
        for field in ("name", "type", "verification_status", "notes"):
            if not isinstance(org.get(field), str) or not org[field].strip():
                errors.append(f"{prefix}.{field} must be a non-empty string")
        if org.get("verification_status") not in ORG_STATES:
            errors.append(f"{prefix}.verification_status is not recognized")
        if "website" in org and not valid_http_url(org["website"]):
            errors.append(f"{prefix}.website must be an http(s) URL")

    source_ids: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"source_records[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        source_id = source.get("id")
        if not valid_id(source_id):
            errors.append(f"{prefix}.id is missing or invalid")
        elif source_id in source_ids:
            errors.append(f"duplicate source id: {source_id}")
        else:
            source_ids.add(source_id)

        if source.get("organization_id") not in organization_ids:
            errors.append(f"{prefix}.organization_id does not reference a known organization")
        if source.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{prefix}.source_type is not recognized")
        if not valid_http_url(source.get("url")):
            errors.append(f"{prefix}.url must be an http(s) URL")
        if source.get("access_status") not in ACCESS_STATES:
            errors.append(f"{prefix}.access_status is not recognized")

        if not isinstance(source.get("polling_enabled"), bool):
            errors.append(f"{prefix}.polling_enabled must be boolean")
        elif source["polling_enabled"]:
            if source.get("access_status") != "approved":
                errors.append(f"{prefix} cannot poll until access_status is approved")
            if source.get("terms_reviewed") is not True:
                errors.append(f"{prefix} cannot poll until terms_reviewed is true")
            if source.get("robots_reviewed") is not True:
                errors.append(f"{prefix} cannot poll until robots_reviewed is true")
            interval = source.get("poll_interval_minutes")
            if not isinstance(interval, int) or interval < 5:
                errors.append(f"{prefix}.poll_interval_minutes must be an integer >= 5")
            if not isinstance(source.get("last_verified_at"), str) or not source["last_verified_at"].strip():
                errors.append(f"{prefix}.last_verified_at is required before polling")

    policy = data.get("verification_policy", {})
    if policy.get("candidate_records_are_not_verified") is not True:
        errors.append("verification_policy.candidate_records_are_not_verified must remain true")

    if errors:
        for error in errors:
            fail(error)
        return 1

    print(
        f"OK: {len(organizations)} organizations and {len(sources)} source records; "
        "IDs, references, URLs, and polling safeguards passed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
