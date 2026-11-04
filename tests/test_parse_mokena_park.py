import unittest
from pathlib import Path

from scripts.parse_mokena_park import parse_html

FIXTURE = Path(__file__).parent.parent / "data" / "fixtures" / "mokena-park-upcoming.html"


class MokenaParkParserTests(unittest.TestCase):
    def setUp(self):
        self.result = parse_html(FIXTURE.read_text(encoding="utf-8"))

    def test_extracts_event_cards(self):
        self.assertEqual(self.result["event_count"], 3)
        self.assertEqual(self.result["events"][0]["title"], "Puzzlemania")

    def test_keeps_registration_deadline_separate(self):
        event = self.result["events"][0]
        self.assertEqual(event["date_text"], "Friday, November 6, 6-8pm")
        self.assertEqual(event["registration_deadline_text"], ["Registration deadline: November 1."])

    def test_does_not_promote_contest_judging_or_deadline_to_event_date(self):
        event = self.result["events"][1]
        self.assertIsNone(event["date_text"])
        self.assertTrue(event["registration_deadline_text"])
        self.assertTrue(any("Judging is December 15" in x for x in event["description"]))

    def test_preserves_explicit_year(self):
        event = self.result["events"][2]
        self.assertEqual(event["date_text"], "Saturday, February 20, 2027, 9am-2pm, Yunker Farm Red Barn")
        self.assertTrue(event["event_date_year_known"])

    def test_resolves_registration_links(self):
        event = self.result["events"][0]
        self.assertTrue(event["links"][0]["url"].startswith("https://secure.rec1.com/"))


if __name__ == "__main__":
    unittest.main()
