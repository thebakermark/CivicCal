#!/usr/bin/env python3
"""Offline parser for Village of Mokena MunicipalCMS calendar HTML.

Supports calendar listing pages (extracting event-detail links) and individual
calendarView.aspx detail pages. It never fetches URLs or guesses dates/timezones.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

SOURCE_ID = "village-of-mokena-events"
SOURCE_URL = "https://www.mokena.gov/calendar.aspx"
DETAIL_PATH = re.compile(r"calendarview\.aspx$", re.IGNORECASE)


class VillagePageParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.text_parts: list[str] = []
        self.headings: list[str] = []
        self.links: list[dict[str, str]] = []
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []
        self._anchor_href: str | None = None
        self._anchor_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = dict(attrs)
        if tag.lower() in {"h1", "h2", "h3", "h4"}:
            self._heading_tag = tag.lower()
            self._heading_parts = []
        if tag.lower() == "a":
            self._anchor_href = attrs_map.get("href")
            self._anchor_parts = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.text_parts.append(data.strip())
        if self._heading_tag:
            self._heading_parts.append(data)
        if self._anchor_href is not None:
            self._anchor_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._heading_tag == tag:
            value = clean(" ".join(self._heading_parts))
            if value:
                self.headings.append(value)
            self._heading_tag = None
            self._heading_parts = []
        if tag == "a" and self._anchor_href is not None:
            label = clean(" ".join(self._anchor_parts))
            href = urljoin(self.page_url, self._anchor_href)
            parsed = urlparse(href)
            if DETAIL_PATH.search(parsed.path) and parse_qs(parsed.query).get("cid"):
                self.links.append({"title": label, "url": href})
            self._anchor_href = None
            self._anchor_parts = []


def clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _page_text(parser: VillagePageParser) -> str:
    # The main page content follows the breadcrumb trail. Avoid including the
    # large repeated navigation/footer when possible.
    text = clean(" ".join(parser.text_parts))
    marker = "Home Government Residents Economic Development How Do I?"
    if marker in text:
        text = text.rsplit(marker, 1)[-1]
    footer = "Show All Calendar Events"
    if footer in text:
        text = text.split(footer, 1)[0]
    return text


def _field(text: str, label: str, following: tuple[str, ...]) -> str | None:
    labels = "|".join(re.escape(x) for x in (label, *following))
    match = re.search(
        rf"{re.escape(label)}\s*(.*?)\s*(?=(?:{labels})\s*|$)",
        text,
        re.IGNORECASE,
    )
    value = clean(match.group(1)) if match else ""
    return value or None


def parse_html(html: str, page_url: str = SOURCE_URL) -> dict:
    parser = VillagePageParser(page_url)
    parser.feed(html)
    parser.close()
    parsed_url = urlparse(page_url)
    query = parse_qs(parsed_url.query)
    is_detail = bool(DETAIL_PATH.search(parsed_url.path) and query.get("cid"))

    if is_detail:
        text = _page_text(parser)
        # MunicipalCMS renders the event title as plain content immediately
        # before Event Date:, not as a heading. The breadcrumb boundary above
        # separates it from the repeated site navigation.
        before_date = re.split(r"Event Date\\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]
        title = clean(before_date) or None
        event = {
            "source_id": SOURCE_ID,
            "source_url": SOURCE_URL,
            "uid": query.get("cid", [None])[0],
            "title": title,
            "start_text": _field(text, "Event Date:", ("Event Time:", "Location:", "Details:")),
            "time_text": _field(text, "Event Time:", ("Location:", "Details:")),
            "location_text": _field(text, "Location:", ("Details:",)),
            "description": _field(text, "Details:", ()),
            "event_url": page_url,
            "timezone": None,
            "extraction_method": "municipal-cms-calendar-detail-v1",
        }
        return {
            "format": "civiccal.village-events.v1",
            "source_id": SOURCE_ID,
            "source_url": page_url,
            "page_type": "event_detail",
            "event_count": 1 if event["title"] else 0,
            "events": [event] if event["title"] else [],
            "detail_links": [],
            "warnings": [
                "Date and time are retained as source text; timezone and machine timestamps are not inferred.",
                "Detail pages may omit optional location or description fields.",
            ],
        }

    # Listing pages are link indexes. Do not infer event dates from the
    # calendar grid's visual position; resolve each cid detail page separately.
    unique: dict[str, dict[str, str]] = {}
    for link in parser.links:
        unique.setdefault(link["url"], link)
    return {
        "format": "civiccal.village-events.v1",
        "source_id": SOURCE_ID,
        "source_url": page_url,
        "page_type": "calendar_listing",
        "event_count": 0,
        "events": [],
        "detail_links": list(unique.values()),
        "warnings": [
            "Calendar grid dates are not assigned to events by visual position.",
            "Each calendarView.aspx detail page is the authoritative event record.",
            "A listing with no extracted detail links may require a source markup update.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="Saved HTML path, or - for stdin")
    ap.add_argument("--page-url", default=SOURCE_URL)
    ap.add_argument("--output")
    args = ap.parse_args()
    html = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
    rendered = json.dumps(parse_html(html, args.page_url), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
