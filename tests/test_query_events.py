import unittest

from scripts.query_events import QueryError, query_events


def record(event_id, source_id, start, title, categories=None, description=""):
    current = {
        "title": title,
        "description": description,
        "start": {"value": start, "kind": "date" if len(start) == 10 else "date-time"},
        "categories": categories or [],
        "status": "scheduled",
    }
    return {
        "event_id": event_id,
        "source_id": source_id,
        "current": current,
        "revisions": [{"revision": 1}],
        "first_seen_at": "2026-11-01T00:00:00Z",
        "last_seen_at": "2026-11-02T00:00:00Z",
        "lifecycle_status": "scheduled",
    }


def state(*items):
    return {
        "format": "civiccal.identity-state.v1",
        "events": {f"key-{index}": item for index, item in enumerate(items)},
    }


def manifest(*ids):
    return {"format": "civiccal.publication-manifest.v1", "approved_event_ids": list(ids)}


class QueryEventsTests(unittest.TestCase):
    def setUp(self):
        self.state = state(
            record("evt-a", "library", "2026-11-10", "Storytime", ["Storytime"], "Books and songs"),
            record("evt-b", "village", "2026-11-12T18:00:00", "Board Meeting", ["Government"]),
            record("evt-c", "library", "2026-12-01", "Technology Workshop", ["Technology"], "Computer basics"),
        )
        self.manifest = manifest("evt-a", "evt-b", "evt-c")

    def test_only_approved_events_are_returned(self):
        result = query_events(self.state, manifest("evt-b"))
        self.assertEqual([item["event_id"] for item in result["events"]], ["evt-b"])

    def test_date_range_is_inclusive_and_sorted(self):
        result = query_events(self.state, self.manifest, start_date="2026-11-10", end_date="2026-11-12")
        self.assertEqual([item["event_id"] for item in result["events"]], ["evt-a", "evt-b"])

    def test_filters_by_source_category_and_text(self):
        result = query_events(self.state, self.manifest, source_id="library", category="technology", q="computer")
        self.assertEqual([item["event_id"] for item in result["events"]], ["evt-c"])

    def test_pagination_reports_total_and_next_offset(self):
        first = query_events(self.state, self.manifest, limit=2)
        self.assertEqual(first["pagination"]["total"], 3)
        self.assertEqual(first["pagination"]["next_offset"], 2)
        second = query_events(self.state, self.manifest, limit=2, offset=2)
        self.assertEqual([item["event_id"] for item in second["events"]], ["evt-c"])
        self.assertIsNone(second["pagination"]["next_offset"])

    def test_missing_approved_id_is_an_error(self):
        with self.assertRaises(QueryError):
            query_events(self.state, manifest("not-present"))

    def test_invalid_date_range_is_an_error(self):
        with self.assertRaises(QueryError):
            query_events(self.state, self.manifest, start_date="2026-11-20", end_date="2026-11-01")

    def test_invalid_pagination_is_an_error(self):
        with self.assertRaises(QueryError):
            query_events(self.state, self.manifest, limit=101)
        with self.assertRaises(QueryError):
            query_events(self.state, self.manifest, offset=-1)


    def test_public_projection_excludes_internal_source_payloads(self):
        internal = record("evt-private", "library", "2026-11-10", "Program")
        internal["current"]["source_record"] = {"private_admin_note": "must not leak"}
        internal["current"]["capture"] = {"headers": {"set-cookie": "secret"}}
        result = query_events(state(internal), manifest("evt-private"))
        event = result["events"][0]["event"]
        self.assertNotIn("source_record", event)
        self.assertNotIn("capture", event)
        self.assertNotIn("private_admin_note", str(event))

    def test_date_filter_excludes_unparseable_dates(self):
        bad = record("evt-x", "other", "not-a-date", "Unclear date")
        result = query_events(state(bad), manifest("evt-x"), start_date="2026-11-01")
        self.assertEqual(result["events"], [])


if __name__ == "__main__":
    unittest.main()
