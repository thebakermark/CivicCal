import copy
import unittest

from scripts.normalize_events import (
    NormalizationError, normalize_document, normalize_event,
    normalize_temporal, parse_date_text, parse_time_text,
)


class NormalizeEventsTests(unittest.TestCase):
    def test_ics_date_only_is_all_day(self):
        event = {"uid": "a", "title": "Holiday",
                 "start": {"value": "2026-11-11", "kind": "date", "timezone": None, "utc": False},
                 "end": None, "all_day": True}
        result = normalize_event(event, "school")
        self.assertEqual(result["start"]["value"], "2026-11-11")
        self.assertTrue(result["all_day"])
        self.assertEqual(result["time_status"], "date_only")

    def test_ics_tzid_is_preserved(self):
        value, status = normalize_temporal(
            {"value": "2026-11-04T18:30:00", "kind": "date-time",
             "timezone": "America/Chicago", "utc": False})
        self.assertEqual(value["timezone"], "America/Chicago")
        self.assertEqual(status, "zoned")

    def test_ics_floating_time_stays_floating(self):
        value, status = normalize_temporal(
            {"value": "2026-11-04T18:30:00", "kind": "date-time",
             "timezone": None, "utc": False})
        self.assertIsNone(value["timezone"])
        self.assertEqual(status, "floating")

    def test_utc_is_marked(self):
        value, status = normalize_temporal(
            {"value": "2026-11-04T18:30:00", "kind": "date-time",
             "timezone": "UTC", "utc": True})
        self.assertEqual(status, "utc")

    def test_iso_schema_datetime_with_offset(self):
        value, status = normalize_temporal("2026-11-04T18:30:00-06:00")
        self.assertEqual(status, "zoned")
        self.assertEqual(value["utc_offset"], "-0600")

    def test_date_parser_requires_explicit_year(self):
        self.assertEqual(parse_date_text("Wednesday, November 4, 2026").isoformat(), "2026-11-04")
        self.assertIsNone(parse_date_text("November 4"))

    def test_explicit_time_range_only(self):
        times = parse_time_text("4:00 PM - 8:00 PM")
        self.assertEqual(times[0].hour, 16)
        self.assertEqual(times[1].hour, 20)
        self.assertIsNone(parse_time_text("4-8 PM"))

    def test_park_registration_deadline_not_event_start(self):
        event = {"title": "Youth program", "date_text": None,
                 "registration_deadline_text": ["Registration Deadline: November 2, 2026"],
                 "fee_text": ["Fee: $10"]}
        result = normalize_event(event, "park")
        self.assertIsNone(result["start"])
        self.assertIn("event_start_missing_or_unparseable", result["data_quality_flags"])
        self.assertEqual(result["registration_deadline"], event["registration_deadline_text"])
        self.assertEqual(result["cost_text"], "Fee: $10")

    def test_park_explicit_date_and_time_are_floating(self):
        event = {"title": "Movie night", "date_text": "November 14, 2026",
                 "time_text": "6:00 PM - 8:00 PM", "event_date_year_known": True}
        result = normalize_event(event, "park")
        self.assertEqual(result["start"]["value"], "2026-11-14T18:00")
        self.assertEqual(result["end"]["value"], "2026-11-14T20:00")
        self.assertEqual(result["time_status"], "floating")
        self.assertIn("timezone_not_assigned", result["data_quality_flags"])

    def test_source_record_is_preserved(self):
        event = {"title": "Town meeting", "start_text": "November 4, 2026",
                 "uid": "cid-42", "custom_field": {"a": 1}}
        original = copy.deepcopy(event)
        result = normalize_event(event, "village")
        self.assertEqual(result["source_record"], original)
        self.assertEqual(event, original)

    def test_normalizes_parse_result_envelope(self):
        document = {"format": "civiccal.parse-result.v1", "source_id": "demo",
                    "capture": {"content_sha256": "abc"},
                    "parser_output": {"format": "civiccal.ics.v1",
                                      "events": [{"uid": "1", "title": "Meeting",
                                                  "start": {"value": "2026-11-04", "kind": "date",
                                                            "timezone": None, "utc": False}}],
                                      "warnings": []}}
        result = normalize_document(document)
        self.assertEqual(result["event_count"], 1)
        self.assertEqual(result["events"][0]["capture"], document["capture"])
        self.assertEqual(result["events"][0]["source_event_id"], "1")

    def test_listing_page_without_events_remains_empty(self):
        document = {"format": "civiccal.parse-result.v1", "source_id": "village",
                    "parser_output": {"format": "civiccal.village-events.v1",
                                      "events": [], "detail_links": [{"url": "https://example.test"}],
                                      "warnings": ["detail links need fetching"]}}
        result = normalize_document(document)
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(result["parser_warnings"], ["detail links need fetching"])

    def test_unsupported_format_rejected(self):
        with self.assertRaises(NormalizationError):
            normalize_document({"format": "unknown", "events": []})

    def test_end_before_start_flagged_not_discarded(self):
        result = normalize_event({
            "title": "Bad interval",
            "start": {"value": "2026-11-04T20:00:00", "kind": "date-time",
                      "timezone": None, "utc": False},
            "end": {"value": "2026-11-04T19:00:00", "kind": "date-time",
                    "timezone": None, "utc": False},
        }, "demo")
        self.assertIn("end_before_start", result["data_quality_flags"])
        self.assertEqual(result["title"], "Bad interval")


if __name__ == "__main__":
    unittest.main()
