#!/usr/bin/env python3
"""Source-specific parser for Mokena Community Park District's Upcoming Events page.

This parser is offline-only. It extracts event cards from saved HTML and keeps
registration deadlines separate from event date text. It never guesses a year.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

SOURCE_ID = "mokena-park-district-upcoming-events"
SOURCE_URL = "https://www.mokenapark.com/upcoming-events-2/"
DATE_HINT = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*,?\s*"
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}"
    r"(?:,\s*\d{4})?\b",
    re.IGNORECASE,
)
DEADLINE_HINT = re.compile(r"\bregistration deadline\s*:", re.IGNORECASE)


class ParkEventsParser(HTMLParser):
    def __init__(self, page_url: str = SOURCE_URL) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.events: list[dict] = []
        self.current: dict | None = None
        self.capture_tag: str | None = None
        self.capture_parts: list[str] = []
        self.capture_href: str | None = None

    def _finish_capture(self) -> None:
        if self.capture_tag is None:
            return
        value = " ".join(" ".join(self.capture_parts).split())
        if value and self.capture_tag in {"h2", "h3", "h4"}:
            if self.current and self.current.get("title"):
                self.events.append(self.current)
            self.current = self._new_event(value)
        elif value and self.current is not None:
            if self.capture_tag == "a":
                if self.capture_href:
                    self.current["links"].append({
                        "text": value,
                        "url": urljoin(self.page_url, self.capture_href),
                    })
            elif self.capture_tag in {"p", "li", "div", "time"}:
                self.current["content"].append(value)
        self.capture_tag = None
        self.capture_parts = []
        self.capture_href = None

    @staticmethod
    def _new_event(title: str) -> dict:
        return {
            "title": title,
            "date_text": None,
            "event_date_year_known": False,
            "description": [],
            "registration_deadline_text": [],
            "location_text": [],
            "fee_text": [],
            "links": [],
            "source_id": SOURCE_ID,
            "source_url": SOURCE_URL,
            "event_url": SOURCE_URL,
            "extraction_method": "mokena-park-html-v1",
        }

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = dict(attrs)
        if tag in {"h2", "h3", "h4"}:
            self._finish_capture()
            self.capture_tag = tag
            self.capture_parts = []
        elif tag in {"p", "li", "time", "div"} and self.current is not None:
            self._finish_capture()
            self.capture_tag = tag
            self.capture_parts = []
        elif tag == "a" and self.current is not None:
            self._finish_capture()
            self.capture_tag = "a"
            self.capture_href = attrs_map.get("href")
            self.capture_parts = []
        elif tag == "br" and self.capture_tag:
            self.capture_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self.capture_tag:
            self.capture_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.capture_tag == tag.lower():
            self._finish_capture()

    def close(self) -> None:
        super().close()
        self._finish_capture()
        if self.current and self.current.get("title"):
            self.events.append(self.current)
            self.current = None


def normalize_records(records: list[dict]) -> list[dict]:
    normalized = []
    for record in records:
        content = record.pop("content", [])
        for line in content:
            if DEADLINE_HINT.search(line):
                record["registration_deadline_text"].append(line)
            elif re.search(r"\bfee\b|\$\s*\d", line, re.IGNORECASE):
                record["fee_text"].append(line)
            elif DATE_HINT.search(line) and record["date_text"] is None:
                record["date_text"] = line
                record["event_date_year_known"] = bool(re.search(r"\b20\d{2}\b", line))
            elif re.search(r"\b(?:The Oaks|Yunker Farm|Park|Recreation & Fitness Center)\b", line, re.IGNORECASE):
                record["location_text"].append(line)
            else:
                record["description"].append(line)
        normalized.append(record)
    return normalized


def parse_html(html: str, page_url: str = SOURCE_URL) -> dict:
    parser = ParkEventsParser(page_url)
    parser.feed(html)
    parser.close()
    events = normalize_records(parser.events)
    return {
        "format": "civiccal.park-district-events.v1",
        "source_id": SOURCE_ID,
        "source_url": page_url,
        "event_count": len(events),
        "events": events,
        "warnings": [
            "Date text without a year is retained but not converted to a timestamp.",
            "Registration deadlines are never treated as event dates.",
            "Editorial sections without an identifiable event date remain undated records for review.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", help="Saved HTML path, or - for stdin")
    ap.add_argument("--page-url", default=SOURCE_URL)
    ap.add_argument("--output")
    args = ap.parse_args()
    html = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8-sig")
    output = json.dumps(parse_html(html, args.page_url), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
