import unittest
from pathlib import Path

from scripts.validate_source_fixtures import validate_fixtures


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
