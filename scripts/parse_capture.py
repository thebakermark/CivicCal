#!/usr/bin/env python3
"""Parse a previously captured CivicCal source payload without network access.

This command reads capture metadata and its archived raw payload, verifies the
payload hash, dispatches to an existing parser/adapter, and writes a separate
parse-result JSON file. It never fetches, changes the registry, or publishes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data" / "sources.json"
ADAPTERS = {"auto", "ics", "jsonld", "mokena_park", "village"}


class HandoffError(Exception):
    """Expected capture validation or parser dispatch error."""


def load_registry_source(registry_path: Path, source_id: str) -> dict:
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"Cannot read source registry: {exc}") from exc
    matches = [row for row in registry.get("source_records", []) if row.get("id") == source_id]
    if len(matches) != 1:
        raise HandoffError(f"Expected exactly one registry source named {source_id!r}; found {len(matches)}.")
    return matches[0]


def load_capture(metadata_path: Path, expected_source_id: str) -> tuple[dict, bytes]:
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HandoffError(f"Cannot read capture metadata: {exc}") from exc

    if metadata.get("format") != "civiccal.raw-capture.v1":
        raise HandoffError("Unsupported capture metadata format.")
    if metadata.get("source_id") != expected_source_id:
        raise HandoffError("Capture metadata source_id does not match --source-id.")
    if metadata.get("outcome") != "captured":
        raise HandoffError("Only successful captures with an archived payload can be parsed.")
    if metadata.get("http_status") != 200:
        raise HandoffError("Only HTTP 200 captures can be parsed; unchanged 304 captures reuse the prior payload.")

    payload_name = metadata.get("raw_payload_file")
    if not isinstance(payload_name, str) or Path(payload_name).name != payload_name:
        raise HandoffError("Capture metadata has no safe raw_payload_file reference.")
    payload_path = metadata_path.parent / payload_name
    try:
        payload = payload_path.read_bytes()
    except OSError as exc:
        raise HandoffError(f"Cannot read archived raw payload: {exc}") from exc

    actual_hash = hashlib.sha256(payload).hexdigest()
    if actual_hash != metadata.get("content_sha256"):
        raise HandoffError("Archived payload SHA-256 does not match capture metadata.")
    return metadata, payload


def capture_summary(metadata: dict, metadata_path: Path, final_url: str | None = None) -> dict:
    """Preserve the capture outcome and page provenance through parsing."""
    return {
        "metadata_file": str(metadata_path),
        "captured_at": metadata.get("captured_at"),
        "content_sha256": metadata.get("content_sha256"),
        "final_url": final_url or metadata.get("final_url"),
        "requested_url": metadata.get("requested_url"),
        "source_url": metadata.get("source_url"),
        "http_status": metadata.get("http_status"),
        "outcome": metadata.get("outcome"),
        "page_role": metadata.get("page_role"),
    }


def select_adapter(requested: str, source_type: str) -> str:
    if requested not in ADAPTERS:
        raise HandoffError(f"Unsupported adapter {requested!r}.")
    if requested != "auto":
        if requested == "ics" and source_type != "ics":
            raise HandoffError("The ICS parser requires an ICS source.")
        if requested in {"jsonld", "mokena_park", "village"} and source_type != "html":
            raise HandoffError(f"The {requested} adapter requires an HTML source.")
        return requested
    if source_type == "ics":
        return "ics"
    if source_type == "html":
        return "jsonld"
    raise HandoffError(
        f"No automatic parser is registered for source type {source_type!r}; choose an explicit adapter."
    )


def parse_payload(payload: bytes, adapter: str, source_id: str, page_url: str) -> dict:
    try:
        source_text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HandoffError("Captured payload is not valid UTF-8; no replacement decoding was attempted.") from exc

    if adapter == "ics":
        from scripts.parse_ics import parse_ics
        return parse_ics(source_text, source_id=source_id, source_url=page_url)

    if adapter == "jsonld":
        from scripts.parse_html import parse_html
        return parse_html(source_text, page_url=page_url, source_id=source_id)

    if adapter == "mokena_park":
        from scripts.parse_mokena_park import parse_html
        result = parse_html(source_text, page_url=page_url)
    elif adapter == "village":
        from scripts.parse_village import parse_html
        result = parse_html(source_text, page_url=page_url)
    else:
        raise HandoffError(f"No parser implementation for adapter {adapter!r}.")

    # The existing source-specific parsers currently have fixed default source
    # identifiers. The handoff binds their observations to the registry source.
    result["source_id"] = source_id
    result["source_url"] = page_url
    for event in result.get("events", []):
        event["source_id"] = source_id
        event["source_url"] = page_url
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--capture-metadata", required=True, type=Path)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--adapter", choices=sorted(ADAPTERS), default="auto")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        source = load_registry_source(args.registry, args.source_id)
        metadata, payload = load_capture(args.capture_metadata, args.source_id)
        source_type = source.get("source_type")
        adapter = select_adapter(args.adapter, source_type)
        page_url = metadata.get("final_url") or source.get("url")
        if not isinstance(page_url, str) or urlparse(page_url).scheme not in {"https", "http"}:
            raise HandoffError("Capture has no usable source page URL.")

        parsed = parse_payload(payload, adapter, args.source_id, page_url)
        result = {
            "format": "civiccal.parse-result.v1",
            "source_id": args.source_id,
            "adapter": adapter,
            "capture": capture_summary(metadata, args.capture_metadata, page_url),
            "parser_output": parsed,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Parsed {parsed.get('event_count', 0)} event record(s) from {args.source_id} using {adapter}.")
        if parsed.get("warnings"):
            print(f"Parser warnings: {len(parsed['warnings'])}; inspect {args.output}.")
        print(f"Parse result: {args.output}")
        return 0
    except HandoffError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
