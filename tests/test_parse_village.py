import unittest

from scripts.parse_village import parse_html


DETAIL_URL = "https://mokenail.municipalone.com/calendarView.aspx?catid=0&cid=30642&id=0"


class VillageParserTests(unittest.TestCase):
    def test_parses_event_detail_fields_without_guessing_timezone(self):
        html = """<!doctype html><html><body><nav>Home Government Residents Economic Development How Do I?</nav><main>
        <h1>Village of Mokena's Food Trucks on Front</h1>
        <div>Event Date:</div><div>Wednesday September 16, 2026</div>
        <div>Event Time:</div><div>4:00 PM - 8:00 PM</div>
        <div>Location:</div><div>Front Street<br>11120 Front Street<br>Mokena IL 60448</div>
        <div>Details:</div><div>Food trucks on Front Street.</div>
        <a href="calendar.aspx">Show All Calendar Events</a>
        </main></body></html>"""
        result = parse_html(html, DETAIL_URL)
        event = result["events"][0]
        self.assertEqual(result["page_type"], "event_detail")
        self.assertEqual(event["uid"], "30642")
        self.assertEqual(event["title"], "Village of Mokena's Food Trucks on Front")
        self.assertEqual(event["start_text"], "Wednesday September 16, 2026")
        self.assertEqual(event["time_text"], "4:00 PM - 8:00 PM")
        self.assertIn("11120 Front Street", event["location_text"])
        self.assertIsNone(event["timezone"])

    def test_listing_extracts_and_deduplicates_detail_links(self):
        html = """<html><body><main>
        <a href="calendarView.aspx?catid=0&amp;cid=30642&amp;id=0">Food Trucks</a>
        <a href="calendarView.aspx?cid=30379">Board Meeting</a>
        <a href="calendarView.aspx?cid=30379">Board Meeting duplicate link</a>
        </main></body></html>"""
        result = parse_html(html, "https://www.mokena.gov/calendar.aspx")
        self.assertEqual(result["page_type"], "calendar_listing")
        self.assertEqual(len(result["detail_links"]), 2)
        self.assertIn("cid=30642", result["detail_links"][0]["url"])

    def test_unrelated_links_are_ignored(self):
        html = '<a href="/about">About</a><a href="calendarView.aspx?cid=123">Event</a>'
        result = parse_html(html, "https://www.mokena.gov/calendar.aspx")
        self.assertEqual(len(result["detail_links"]), 1)


if __name__ == "__main__":
    unittest.main()
