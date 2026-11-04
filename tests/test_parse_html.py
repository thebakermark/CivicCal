import unittest

from scripts.parse_html import parse_html


class HtmlEventParserTests(unittest.TestCase):
    def test_extracts_event_from_json_ld(self):
        html = """
        <html><head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Event",
          "@id": "#event-1",
          "name": "Community Picnic",
          "description": "Food and games",
          "startDate": "2027-06-12T12:00:00-05:00",
          "endDate": "2027-06-12T16:00:00-05:00",
          "url": "/events/picnic",
          "location": {
            "@type": "Place",
            "name": "Community Park",
            "address": {"@type": "PostalAddress", "addressLocality": "Mokena"}
          },
          "offers": {"@type": "Offer", "url": "/register", "price": "5", "priceCurrency": "USD"},
          "isAccessibleForFree": false
        }
        </script></head></html>
        """
        result = parse_html(html, "https://example.org/calendar/", "park")
        self.assertEqual(result["event_count"], 1)
        event = result["events"][0]
        self.assertEqual(event["title"], "Community Picnic")
        self.assertEqual(event["start"], "2027-06-12T12:00:00-05:00")
        self.assertEqual(event["url"], "https://example.org/events/picnic")
        self.assertEqual(event["location"]["name"], "Community Park")
        self.assertEqual(event["offers"][0]["url"], "https://example.org/register")
        self.assertFalse(event["is_accessible_for_free"])
        self.assertEqual(event["source_id"], "park")

    def test_walks_graph_and_multiple_events(self):
        html = """
        <script type="application/ld+json">
        {"@graph":[
          {"@type":"Organization","name":"Organizer"},
          {"@type":["https://schema.org/Event"],"name":"A","startDate":"2027-01-01"},
          {"@type":"Event","name":"B","startDate":"2027-01-02"}
        ]}
        </script>
        """
        result = parse_html(html, "https://example.org", "village")
        self.assertEqual([e["title"] for e in result["events"]], ["A", "B"])

    def test_invalid_json_ld_is_reported_not_fatal(self):
        result = parse_html(
            '<script type="application/ld+json">{bad}</script>',
            "https://example.org", "x"
        )
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(len(result["warnings"]), 1)

    def test_non_event_json_ld_is_ignored(self):
        result = parse_html(
            '<script type="application/ld+json">{"@type":"Organization","name":"Town"}</script>',
            "https://example.org", "x"
        )
        self.assertEqual(result["events"], [])

    def test_no_dates_are_invented(self):
        result = parse_html(
            '<script type="application/ld+json">{"@type":"Event","name":"TBD"}</script>',
            "https://example.org", "x"
        )
        self.assertIsNone(result["events"][0]["start"])


if __name__ == "__main__":
    unittest.main()
