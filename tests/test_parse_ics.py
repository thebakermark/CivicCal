import unittest

from scripts.parse_ics import parse_ics, unfold_lines, unescape_text


class ParseICSTests(unittest.TestCase):
    def parse_one(self, body):
        result = parse_ics("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n" + body + "\r\nEND:VCALENDAR\r\n", "test-source")
        self.assertEqual(result["event_count"], 1)
        return result["events"][0]

    def test_utc_datetime(self):
        event = self.parse_one("BEGIN:VEVENT\r\nUID:a\r\nDTSTART:20261103T180000Z\r\nDTEND:20261103T190000Z\r\nSUMMARY:Town meeting\r\nEND:VEVENT")
        self.assertEqual(event["start"]["value"], "2026-11-03T18:00:00")
        self.assertEqual(event["start"]["timezone"], "UTC")
        self.assertFalse(event["all_day"])

    def test_tzid_preserves_local_wall_time(self):
        event = self.parse_one("BEGIN:VEVENT\r\nUID:b\r\nDTSTART;TZID=America/Chicago:20261103T120000\r\nEND:VEVENT")
        self.assertEqual(event["start"]["value"], "2026-11-03T12:00:00")
        self.assertEqual(event["start"]["timezone"], "America/Chicago")

    def test_floating_time_has_no_guessed_zone(self):
        event = self.parse_one("BEGIN:VEVENT\r\nUID:c\r\nDTSTART:20261103T120000\r\nEND:VEVENT")
        self.assertIsNone(event["start"]["timezone"])
        self.assertFalse(event["start"]["utc"])

    def test_all_day_date(self):
        event = self.parse_one("BEGIN:VEVENT\r\nUID:d\r\nDTSTART;VALUE=DATE:20261103\r\nEND:VEVENT")
        self.assertTrue(event["all_day"])
        self.assertEqual(event["start"]["kind"], "date")

    def test_cancelled_event(self):
        event = self.parse_one("BEGIN:VEVENT\r\nUID:e\r\nSTATUS:CANCELLED\r\nEND:VEVENT")
        self.assertTrue(event["cancelled"])
        self.assertEqual(event["status"], "CANCELLED")

    def test_folded_and_escaped_text(self):
        raw = "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:f\r\nSUMMARY:Community plan\r\n ning\r\nDESCRIPTION:Bring water\\, snacks\\nand chairs\\; please\\!\r\nEND:VEVENT\r\nEND:VCALENDAR"
        event = parse_ics(raw)["events"][0]
        self.assertEqual(event["title"], "Community planning")
        self.assertEqual(event["description"], "Bring water, snacks\nand chairs; please!")

    def test_recurrence_is_preserved_not_expanded(self):
        event = self.parse_one("BEGIN:VEVENT\r\nUID:g\r\nDTSTART:20261103T120000Z\r\nRRULE:FREQ=WEEKLY;COUNT=4\r\nEXDATE:20261110T120000Z\r\nEND:VEVENT")
        self.assertEqual(event["recurrence_rule"], "FREQ=WEEKLY;COUNT=4")
        self.assertEqual(event["exception_dates"], ["20261110T120000Z"])

    def test_metadata_and_categories(self):
        event = self.parse_one("BEGIN:VEVENT\r\nUID:h\r\nSEQUENCE:3\r\nSUMMARY:Food drive\r\nCATEGORIES:Community,Volunteer\r\nLOCATION:Village Hall\\, Mokena\r\nEND:VEVENT")
        self.assertEqual(event["sequence"], 3)
        self.assertEqual(event["categories"], ["Community", "Volunteer"])
        self.assertEqual(event["location"], "Village Hall, Mokena")

    def test_unfolding(self):
        self.assertEqual(unfold_lines("SUMMARY:Long\r\n text"), ["SUMMARY:Longtext"])
        self.assertEqual(unescape_text(r"a\\b\,c"), "a\\b,c")


if __name__ == "__main__":
    unittest.main()
