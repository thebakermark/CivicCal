import unittest

from scripts.parse_village import parse_html


DETAIL_URL = "https://mokenail.municipalone.com/calendarView.aspx?catid=0&cid=30642&id=0"


class VillageParserTests(unittest.TestCase):
    def test_parses_event_detail_fields_without_guessing_timezone(self):
        html = """<!doctype html><html><body><nav>Home Government Residents Economic Development How Do I?</nav><main>
        <div>Village of Mokena's Food Trucks on Front</div>
        <div>Event Date:</div><div>Wednesday September 16, 2026</div>
        <div>Event Time:</div><div>4:00 PM - 8:00 PM</div>
        <div>Location:</div><div>Front Street<br>11120 Front Street<br>Mokena IL 60448</div>
        <div>Details:</div>
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
        self.assertIsNone(event["description"])

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

    def test_listing_exposes_rel_next_but_never_claims_terminal_page(self):
        html = """<html><body>
        <a href="calendarView.aspx?cid=123">Event</a>
        <a rel="next" href="calendar.aspx?page=2">Next</a>
        </body></html>"""
        result = parse_html(html, "https://www.mokena.gov/calendar.aspx")
        self.assertEqual(result["pagination"]["strategy"], "rel_next")
        self.assertEqual(result["pagination"]["next_page_urls"], ["https://www.mokena.gov/calendar.aspx?page=2"])
        self.assertFalse(result["pagination"]["terminal_page_confirmed"])
        self.assertEqual(result["pagination"]["completeness"], "unknown")

    def test_no_rel_next_does_not_claim_listing_is_complete(self):
        result = parse_html("<html><body><a href='calendarView.aspx?cid=123'>Event</a></body></html>",
                            "https://www.mokena.gov/calendar.aspx")
        self.assertEqual(result["pagination"]["next_page_urls"], [])
        self.assertFalse(result["pagination"]["terminal_page_confirmed"])
        self.assertIn("No explicit rel=last", result["pagination"]["evidence"])

    def test_rel_last_confirms_terminal_page_only_when_current_url_matches(self):
        html = """<html><body>
        <a rel="last" href="calendar.aspx?page=3">Last</a>
        </body></html>"""
        terminal = parse_html(html, "https://www.mokena.gov/calendar.aspx?page=3")
        self.assertEqual(terminal["pagination"]["last_page_urls"],
                         ["https://www.mokena.gov/calendar.aspx?page=3"])
        self.assertTrue(terminal["pagination"]["terminal_page_confirmed"])
        earlier = parse_html(html, "https://www.mokena.gov/calendar.aspx?page=2")
        self.assertFalse(earlier["pagination"]["terminal_page_confirmed"])

    def test_unrelated_links_are_ignored(self):
        html = '<a href="/about">About</a><a href="calendarView.aspx?cid=123">Event</a>'
        result = parse_html(html, "https://www.mokena.gov/calendar.aspx")
        self.assertEqual(len(result["detail_links"]), 1)


if __name__ == "__main__":
    unittest.main()
