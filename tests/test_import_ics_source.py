import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_ics_source import (
    ImportErrorSafe,
    compare_snapshots,
    event_map,
    load_source,
)


def sample_event(uid, title="Holiday"):
    return {
        "uid": uid,
        "title": title,
        "start": {"value": "2027-12-24", "kind": "date", "timezone": None, "utc": False},
        "end": {"value": "2027-12-25", "kind": "date", "timezone": None, "utc": False},
        "source_id": "sample",
        "source_url": "https://example.org/calendar.ics",
    }


class ImporterTests(unittest.TestCase):
    def write_registry(self, directory, source):
        path = Path(directory) / "sources.json"
        path.write_text(json.dumps({"source_records": [source]}), encoding="utf-8")
        return path

    def source(self, **overrides):
        value = {
            "id": "approved-calendar",
            "source_type": "ics",
            "url": "https://example.org/calendar.ics",
            "access_status": "approved",
            "terms_reviewed": True,
            "robots_reviewed": True,
            "polling_enabled": False,
        }
        value.update(overrides)
        return value

    def test_manual_fetch_requires_approved_source_even_when_polling_is_off(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = self.write_registry(directory, self.source(access_status="review_required"))
            with self.assertRaisesRegex(ImportErrorSafe, "not approved"):
                load_source(registry, "approved-calendar")

    def test_manual_fetch_requires_terms_and_robots_review(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = self.write_registry(directory, self.source(robots_reviewed=False))
            with self.assertRaisesRegex(ImportErrorSafe, "terms_reviewed=true"):
                load_source(registry, "approved-calendar")

    def test_approved_source_can_be_fetched_without_enabling_polling(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = self.write_registry(directory, self.source(polling_enabled=False))
            source = load_source(registry, "approved-calendar")
            self.assertFalse(source["polling_enabled"])

    def test_missing_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = self.write_registry(directory, self.source())
            with self.assertRaisesRegex(ImportErrorSafe, "found 0"):
                load_source(registry, "not-there")

    def test_baseline_marks_every_event_as_baseline_not_new_announcement(self):
        current = {"calendar": {"events": [sample_event("a"), sample_event("b")]}}
        report = compare_snapshots(None, current)
        self.assertEqual(report["comparison"], "baseline")
        self.assertEqual(report["added"], ["a", "b"])
        self.assertIn("baseline", report["note"])

    def test_comparison_reports_added_changed_and_missing_without_cancelling(self):
        previous = {"calendar": {"events": [sample_event("keep"), sample_event("gone")]}}
        current = {"calendar": {"events": [sample_event("keep", "Updated Holiday"), sample_event("new")]}}
        report = compare_snapshots(previous, current)
        self.assertEqual(report["added"], ["new"])
        self.assertEqual(report["missing"], ["gone"])
        self.assertEqual([row["uid"] for row in report["changed"]], ["keep"])
        self.assertIn("not a cancellation", report["note"])

    def test_duplicate_uids_are_rejected(self):
        with self.assertRaisesRegex(ImportErrorSafe, "repeated UID"):
            event_map({"events": [sample_event("same"), sample_event("same")]})

    def test_provenance_url_change_is_not_event_content_change(self):
        before = sample_event("one")
        after = dict(before, source_url="https://example.org/new-url")
        report = compare_snapshots(
            {"calendar": {"events": [before]}},
            {"calendar": {"events": [after]}},
        )
        self.assertEqual(report["changed"], [])


if __name__ == "__main__":
    unittest.main()
