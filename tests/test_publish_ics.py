import unittest

from scripts.publish_ics import FeedError, build_calendar, _fold
from scripts.parse_ics import parse_ics


def identity_record(event_id="evt_123", status="scheduled", **overrides):
    current = {
        "title": "Village Meeting",
        "description": "Public meeting, bring questions.\nDoors open at 6.",
        "start": {"value": "2026-11-04T18:00:00-06:00", "kind": "date-time"},
        "end": {"value": "2026-11-04T19:00:00-06:00", "kind": "date-time"},
        "time_status": "zoned",
        "status": status,
        "location": {"name": "Village Hall"},
        "categories": ["Government", "Public Meeting"],
        "event_url": "https://example.org/meeting",
        "registration_url": None,
        "recurrence": None,
    }
    current.update(overrides)
    return {
        "event_id": event_id,
        "source_id": "village-calendar",
        "current": current,
        "revisions": [{"revision": 3, "observed_at": "2026-11-04T18:00:00Z"}],
    }


def state_with(*records):
    return {
        "format": "civiccal.identity-state.v1",
        "events": {f"key-{i}": record for i, record in enumerate(records)},
    }


def manifest(*event_ids):
    return {
        "format": "civiccal.publication-manifest.v1",
        "calendar_name": "Mokena Community Events",
        "approved_event_ids": list(event_ids),
    }


class PublishICSTests(unittest.TestCase):
    def test_generates_stable_uid_sequence_and_utc_times(self):
        text, summary = build_calendar(state_with(identity_record()), manifest("evt_123"))
        self.assertIn("UID:evt_123@civiccal\r\n", text)
        self.assertIn("SEQUENCE:3\r\n", text)
        self.assertIn("DTSTART:20261105T000000Z\r\n", text)
        self.assertIn("DTEND:20261105T010000Z\r\n", text)
        self.assertEqual(summary["published_count"], 1)

    def test_escapes_text_and_preserves_line_breaks(self):
        text, _ = build_calendar(state_with(identity_record()), manifest("evt_123"))
        self.assertIn(r"SUMMARY:Village Meeting", text)
        self.assertIn(r"DESCRIPTION:Public meeting\, bring questions.\nDoors open at 6.", text)
        self.assertIn(r"CATEGORIES:Government,Public Meeting", text)
        self.assertIn(r"LOCATION:Village Hall", text)

    def test_only_manifest_approved_events_are_included(self):
        state = state_with(identity_record(), identity_record("evt_456"))
        text, summary = build_calendar(state, manifest("evt_456"))
        self.assertNotIn("evt_123@civiccal", text)
        self.assertIn("evt_456@civiccal", text)
        self.assertEqual(summary["published_count"], 1)

    def test_cancelled_status_is_explicit(self):
        text, _ = build_calendar(state_with(identity_record(status="cancelled")), manifest("evt_123"))
        self.assertIn("STATUS:CANCELLED\r\n", text)


    def test_explicit_utc_semantics_with_normalized_naive_value_emit_z(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2026-11-04T18:00:00", "kind": "date-time", "timezone": None},
            "end": {"value": "2026-11-04T19:00:00", "kind": "date-time", "timezone": None},
            "time_status": "utc",
            "timezone": None,
        })
        text, _ = build_calendar(state_with(record), manifest("evt_123"))
        self.assertIn("DTSTART:20261104T180000Z", text)
        self.assertIn("DTEND:20261104T190000Z", text)

    def test_floating_time_is_not_assigned_a_timezone(self):
        record = identity_record()
        record["current"]["start"] = {"value": "2026-11-04T18:00:00", "kind": "date-time"}
        record["current"]["end"] = {"value": "2026-11-04T19:00:00", "kind": "date-time"}
        record["current"]["time_status"] = "floating"
        text, _ = build_calendar(state_with(record), manifest("evt_123"))
        self.assertIn("DTSTART:20261104T180000\r\n", text)
        self.assertNotIn("20261105T000000Z", text)

    def test_date_only_event_uses_value_date(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2026-11-04", "kind": "date"},
            "end": None,
            "time_status": "date_only",
        })
        text, _ = build_calendar(state_with(record), manifest("evt_123"))
        self.assertIn("DTSTART;VALUE=DATE:20261104\r\n", text)

    def test_all_day_end_is_only_emitted_when_explicitly_exclusive(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2026-11-04", "kind": "date"},
            "end": {"value": "2026-11-06", "kind": "date"},
            "time_status": "date_only",
            "end_exclusive": True,
        })
        text, _ = build_calendar(state_with(record), manifest("evt_123"))
        self.assertIn("DTEND;VALUE=DATE:20261106\r\n", text)


    def test_ambiguous_all_day_end_is_rejected(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2026-11-04", "kind": "date"},
            "end": {"value": "2026-11-06", "kind": "date"},
            "time_status": "date_only",
        })
        with self.assertRaises(FeedError):
            build_calendar(state_with(record), manifest("evt_123"))

    def test_unknown_timezone_semantics_rejected(self):
        record = identity_record()
        record["current"]["start"] = {"value": "2026-11-04T18:00:00", "kind": "date-time"}
        record["current"]["time_status"] = "zoned"
        with self.assertRaises(FeedError):
            build_calendar(state_with(record), manifest("evt_123"))


    def test_iana_timezone_emits_vtimezone_and_preserves_local_wall_time(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2027-03-14T09:00:00", "kind": "date-time"},
            "end": {"value": "2027-03-14T10:00:00", "kind": "date-time"},
            "time_status": "zoned",
            "timezone": "America/Chicago",
        })
        text, _ = build_calendar(state_with(record), manifest("evt_123"))
        self.assertIn("BEGIN:VTIMEZONE\r\nTZID:America/Chicago", text)
        self.assertIn("TZOFFSETFROM:-0600", text)
        self.assertIn("TZOFFSETTO:-0500", text)
        self.assertIn("DTSTART;TZID=America/Chicago:20270314T090000", text)
        self.assertIn("DTEND;TZID=America/Chicago:20270314T100000", text)
        parsed = parse_ics(text, source_id="roundtrip")
        self.assertEqual(parsed["events"][0]["start"]["value"], "2027-03-14T09:00:00")
        self.assertEqual(parsed["events"][0]["start"]["timezone"], "America/Chicago")



    def test_fixed_offset_iana_zone_emits_standard_observance(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2027-03-14T09:00:00", "kind": "date-time"},
            "end": {"value": "2027-03-14T10:00:00", "kind": "date-time"},
            "time_status": "zoned",
            "timezone": "Etc/GMT+5",
        })
        text, _ = build_calendar(state_with(record), manifest("evt_123"))
        self.assertIn("BEGIN:STANDARD", text)
        self.assertIn("TZOFFSETFROM:-0500", text)
        self.assertIn("TZOFFSETTO:-0500", text)

    def test_nonexistent_daylight_saving_wall_time_is_rejected(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2027-03-14T02:30:00", "kind": "date-time"},
            "time_status": "zoned",
            "timezone": "America/Chicago",
        })
        with self.assertRaises(FeedError):
            build_calendar(state_with(record), manifest("evt_123"))

    def test_ambiguous_daylight_saving_wall_time_requires_offset(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2026-11-01T01:30:00", "kind": "date-time"},
            "time_status": "zoned",
            "timezone": "America/Chicago",
        })
        with self.assertRaises(FeedError):
            build_calendar(state_with(record), manifest("evt_123"))

    def test_unknown_iana_timezone_is_rejected(self):
        record = identity_record()
        record["current"].update({
            "start": {"value": "2027-03-14T09:00:00", "kind": "date-time"},
            "time_status": "zoned",
            "timezone": "Mars/Olympus_Mons",
        })
        with self.assertRaises(FeedError):
            build_calendar(state_with(record), manifest("evt_123"))

    def test_recurrence_rejected_until_supported(self):
        record = identity_record()
        record["current"]["recurrence"] = {"rule": "FREQ=WEEKLY"}
        with self.assertRaises(FeedError):
            build_calendar(state_with(record), manifest("evt_123"))

    def test_invalid_or_unapproved_ids_rejected(self):
        with self.assertRaises(FeedError):
            build_calendar(state_with(identity_record()), manifest("missing"))
        with self.assertRaises(FeedError):
            build_calendar(state_with(identity_record()), {
                "format": "civiccal.publication-manifest.v1",
                "approved_event_ids": ["evt_123", "evt_123"],
            })


    def test_generated_feed_round_trips_through_ics_parser(self):
        generated, _ = build_calendar(state_with(identity_record()), manifest("evt_123"))
        parsed = parse_ics(generated, source_id="roundtrip")
        self.assertEqual(parsed["event_count"], 1)
        event = parsed["events"][0]
        self.assertEqual(event["uid"], "evt_123@civiccal")
        self.assertEqual(event["title"], "Village Meeting")
        self.assertEqual(event["description"], "Public meeting, bring questions.\nDoors open at 6.")
        self.assertEqual(event["status"], "CONFIRMED")
        self.assertEqual(event["start"]["kind"], "date-time")
        self.assertTrue(event["start"]["utc"])

    def test_utf8_line_folding_respects_octet_limit(self):
        folded = _fold("SUMMARY:" + "🎈" * 50)
        for line in folded.split("\r\n"):
            self.assertLessEqual(len(line.encode("utf-8")), 75)
        self.assertTrue(folded.split("\r\n")[1].startswith(" "))


if __name__ == "__main__":
    unittest.main()
