#!/usr/bin/env python3
"""Offline-first HTML event extractor for CivicCal.

Extracts Schema.org Event records from JSON-LD. It does not fetch pages,
execute JavaScript, follow links, or infer dates from arbitrary page text.
"""
from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin


class JsonLdCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._capture = False
        self._parts: list[str] = []
        self.documents: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        values = {key.lower(): value for key, value in attrs}
        content_type = (values.get("type") or "").split(";", 1)[0].strip().lower()
        if content_type == "application/ld+json":
            self._capture = True
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._capture:
            self.documents.append("".join(self._parts))
            self._capture = False
            self._parts = []


def _types(value: Any) -> set[str]:
    raw = value if isinstance(value, list) else [value]
    return {str(item).rsplit("/", 1)[-1].rsplit("#", 1)[-1] for item in raw if item}


def _objects(node: Any):
    if isinstance(node, list):
        for item in node:
            yield from _objects(item)
    elif isinstance(node, dict):
        if "Event" in _types(node.get("@type")):
            yield node
        if "@graph" in node:
            yield from _objects(node["@graph"])


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("name") or value.get("text") or value.get("@id")
    if isinstance(value, list):
        value = "; ".join(filter(None, (_text(item) for item in value)))
    if value is None:
        return None
    result = " ".join(str(value).split())
    return result or None


def _location(value: Any) -> dict[str, Any] | None:
    if not value:
        return None
    if isinstance(value, list):
        return {"items": [item for item in (_location(v) for v in value) if item]}
    if isinstance(value, str):
        return {"name": value}
    if not isinstance(value, dict):
        return {"name": str(value)}
    address = value.get("address")
    if isinstance(address, dict):
        address = {key: address.get(key) for key in
                   ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")
                   if address.get(key) is not None}
    return {
        "name": _text(value.get("name")),
        "url": value.get("url") or value.get("@id"),
        "address": address,
    }


def normalize_event(item: dict[str, Any], page_url: str, source_id: str) -> dict[str, Any]:
    raw_url = item.get("url") or item.get("@id")
    event_url = urljoin(page_url, raw_url) if isinstance(raw_url, str) else page_url
    offers = item.get("offers")
    if isinstance(offers, dict):
        offers = [offers]
    normalized_offers = []
    for offer in offers if isinstance(offers, list) else []:
        if isinstance(offer, dict):
            normalized_offers.append({
                "url": urljoin(page_url, offer["url"]) if offer.get("url") else None,
                "price": offer.get("price"),
                "price_currency": offer.get("priceCurrency"),
                "availability": offer.get("availability"),
                "valid_from": offer.get("validFrom"),
            })
    organizer = item.get("organizer")
    return {
        "source_id": source_id,
        "source_url": page_url,
        "uid": item.get("identifier") or item.get("@id"),
        "title": _text(item.get("name")),
        "description": _text(item.get("description")),
        "start": item.get("startDate"),
        "end": item.get("endDate"),
        "timezone": None,
        "location": _location(item.get("location")),
        "url": event_url,
        "status": _text(item.get("eventStatus")),
        "event_attendance_mode": _text(item.get("eventAttendanceMode")),
        "organizer": _text(organizer),
        "offers": normalized_offers,
        "is_accessible_for_free": item.get("isAccessibleForFree"),
        "audience": _text(item.get("audience")),
        "image": urljoin(page_url, item["image"]) if isinstance(item.get("image"), str) else None,
        "extraction_method": "schema.org-json-ld",
    }


def parse_html(html: str, page_url: str, source_id: str = "unassigned") -> dict[str, Any]:
    collector = JsonLdCollector()
    collector.feed(html)
    events: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, raw in enumerate(collector.documents, 1):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            warnings.append(f"JSON-LD block {index}: invalid JSON ({exc.msg}).")
            continue
        for item in _objects(payload):
            events.append(normalize_event(item, page_url, source_id))
    # Do not collapse identical records: separate source records are provenance.
    return {
        "format": "civiccal.html-events.v1",
        "source_id": source_id,
        "source_url": page_url,
        "extraction_method": "schema.org-json-ld",
        "event_count": len(events),
        "events": events,
        "warnings": warnings,
        "limitations": [
            "Only Schema.org Event objects in JSON-LD are extracted.",
            "No JavaScript is executed and no network requests are made.",
            "Missing dates, timezone, identifiers, and fields are not guessed.",
            "HTML pages without JSON-LD require a reviewed source-specific adapter.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="HTML file path, or - for standard input")
    parser.add_argument("--page-url", required=True, help="Canonical source page URL")
    parser.add_argument("--source-id", default="unassigned")
    parser.add_argument("--output", help="JSON output path; defaults to stdout")
    args = parser.parse_args()
    raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
    result = parse_html(raw, args.page_url, args.source_id)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
