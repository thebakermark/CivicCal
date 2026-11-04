import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from pathlib import Path

from scripts.validate_source_fixtures import validate_fixtures
from scripts.parse_village import parse_html as parse_village_html
from scripts.normalize_events import normalize_document
from scripts.track_event_identity import process_normalized
from scripts.storage import JsonFileIdentityStateStore
from scripts.query_events import query_events
from scripts.publish_ics import build_calendar
from scripts.parse_ics import parse_ics
from scripts.serve_api import make_handler


class SourceFixtureIntegrationTests(unittest.TestCase):
    def test_three_initial_source_fixtures_validate_together(self):
        report = validate_fixtures(Path(__file__).resolve().parents[1])

        self.assertEqual(report["format"], "civiccal.fixture-validation.v1")
        self.assertEqual(report["mode"], "offline_fixture_only")
        self.assertFalse(report["network_access"])
        self.assertFalse(report["database_writes"])
        self.assertFalse(report["publication"])
        self.assertEqual(report["source_count"], 3)
        self.assertEqual(report["event_count"], 6)
        self.assertEqual(report["normalized_event_count"], 6)
        self.assertEqual(report["review_flagged_event_count"], 5)

        by_source = {source["parser"]: source for source in report["sources"]}
        self.assertEqual(by_source["parse_ics"]["event_count"], 2)
        self.assertEqual(by_source["parse_mokena_park"]["event_count"], 3)
        self.assertEqual(by_source["parse_village"]["event_count"], 1)
        self.assertEqual(by_source["parse_ics"]["normalized_event_count"], 2)
        self.assertEqual(by_source["parse_mokena_park"]["normalized_event_count"], 3)
        self.assertEqual(by_source["parse_village"]["normalized_event_count"], 1)


    def test_village_html_fixture_flows_through_storage_query_and_ics(self):
        root = Path(__file__).resolve().parents[1]
        source_id = "village-of-mokena-events"
        page_url = (
            "https://www.mokena.gov/calendarView.aspx"
            "?catid=0&cid=30642&id=0"
        )
        html = (root / "data/fixtures/village-calendar-detail.html").read_text(
            encoding="utf-8"
        )

        parsed = parse_village_html(html, page_url=page_url)
        parsed["source_id"] = source_id
        for event in parsed["events"]:
            event["source_id"] = source_id
            event["source_url"] = page_url

        normalized = normalize_document(parsed)
        self.assertEqual(normalized["event_count"], 1)
        self.assertEqual(normalized["events"][0]["source_event_id"], "30642")
        self.assertEqual(normalized["events"][0]["time_status"], "floating")

        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "identity-state.json"
            store = JsonFileIdentityStateStore(state_path)
            result, state = process_normalized(
                normalized, store.load_identity_state(),
                observed_at="2026-11-04T12:00:00Z",
            )
            self.assertEqual(result["new_events"], 1)
            store.save_identity_state(state)

            persisted = store.load_identity_state()
            event_record = next(iter(persisted["events"].values()))
            event_id = event_record["event_id"]
            publication = {
                "format": "civiccal.publication-manifest.v1",
                "calendar_name": "Mokena Community Events",
                "approved_event_ids": [event_id],
            }

            queried = query_events(persisted, publication, source_id=source_id)
            self.assertEqual(
                [item["event_id"] for item in queried["events"]], [event_id]
            )

            calendar_text, summary = build_calendar(persisted, publication)
            self.assertEqual(summary["published_count"], 1)
            self.assertIn(f"UID:{event_id}@civiccal", calendar_text)
            self.assertIn("SUMMARY:Village of Mokena's Food Trucks on Front", calendar_text)
            self.assertIn("DTSTART:20260916T160000", calendar_text)
            self.assertIn("DTEND:20260916T200000", calendar_text)

            round_trip = parse_ics(calendar_text, source_id="calendar-round-trip")
            self.assertEqual(round_trip["event_count"], 1)
            self.assertEqual(round_trip["events"][0]["start"]["value"], "2026-09-16T16:00:00")
            self.assertFalse(round_trip["events"][0]["start"]["utc"])

            # Exercise the persisted HTML-derived event through its stable source relay.
            manifest_path = Path(directory) / "publication.json"
            manifest_path.write_text(json.dumps(publication), encoding="utf-8")
            registry_path = Path(directory) / "sources.json"
            registry_path.write_text(json.dumps({
                "source_records": [{"id": source_id, "name": "Village of Mokena Events"}]
            }), encoding="utf-8")
            server = ThreadingHTTPServer(
                ("127.0.0.1", 0),
                make_handler(state_path, manifest_path, registry_path),
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                with urlopen(base + f"/calendars/sources/{source_id}.ics") as response:
                    relay_text = response.read().decode("utf-8")
                    self.assertEqual(response.headers.get_content_type(), "text/calendar")
                self.assertIn(f"UID:{event_id}@civiccal", relay_text)
                self.assertIn("SUMMARY:Village of Mokena's Food Trucks on Front", relay_text)
                with urlopen(base + f"/api/v1/events?source_id={source_id}") as response:
                    relay_json = json.loads(response.read())
                self.assertEqual(
                    [item["event_id"] for item in relay_json["events"]], [event_id]
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_report_includes_warnings_instead_of_hiding_them(self):
        report = validate_fixtures(Path(__file__).resolve().parents[1])
        self.assertEqual(
            report["warning_count"],
            sum(source["warning_count"] for source in report["sources"]),
        )
        for source in report["sources"]:
            self.assertIn("warnings", source)


if __name__ == "__main__":
    unittest.main()
