import json
import unittest
from pathlib import Path

from scripts.classify_school_schedule import classify_event, classify_document


class SchoolScheduleClassificationTests(unittest.TestCase):
    def test_no_school_is_classified(self):
        result = classify_event({"title": "No School - Thanksgiving"})
        self.assertTrue(result["is_schedule_exception"])
        self.assertEqual(result["student_attendance"], "no_school")

    def test_named_break_is_classified(self):
        result = classify_event({"title": "Winter Break"})
        self.assertEqual(result["schedule_type"], "school_break")
        self.assertEqual(result["student_attendance"], "no_school")

    def test_early_release_is_shortened_day(self):
        result = classify_event({"title": "Early Release - Teacher In-Service"})
        self.assertEqual(result["schedule_type"], "early_dismissal")
        self.assertEqual(result["student_attendance"], "shortened_day")

    def test_half_day_is_classified(self):
        result = classify_event({"title": "Half Day"})
        self.assertEqual(result["schedule_type"], "half_day")

    def test_late_start_is_classified(self):
        result = classify_event({"title": "Delayed Start"})
        self.assertEqual(result["schedule_type"], "late_start")
        self.assertEqual(result["student_attendance"], "delayed_start")

    def test_teacher_institute_day_is_flagged_for_attention(self):
        result = classify_event({"title": "Teacher Institute Day"})
        self.assertEqual(result["schedule_type"], "teacher_institute")
        self.assertEqual(result["student_attendance"], "confirm_student_attendance")

    def test_unrelated_school_event_is_not_exception(self):
        result = classify_event({"title": "School Board Meeting"})
        self.assertFalse(result["is_schedule_exception"])
        self.assertEqual(result["student_attendance"], "unknown")

    def test_schedule_text_in_description_is_considered(self):
        result = classify_event({
            "title": "District Calendar Notice",
            "description": "Students will not attend school on this date."
        })
        self.assertTrue(result["is_schedule_exception"])

    def test_document_requires_registered_school_source(self):
        document = {"format": "civiccal.normalized-events.v1", "source_id": "school-a",
                    "events": [{"title": "No School"}]}
        result = classify_document(document, {"school-a"})
        self.assertTrue(result["events"][0]["school_schedule"]["is_schedule_exception"])
        with self.assertRaises(ValueError):
            classify_document(document, {"park-district"})

    def test_verified_summit_hill_calendar_fixture_classifies_all_exceptions(self):
        path = Path(__file__).parents[1] / "data/fixtures/summit-hill-2026-27-school-schedule.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(fixture["school_year"], "2026-2027")
        self.assertEqual(len(fixture["events"]), 18)
        for source_event in fixture["events"]:
            actual = classify_event({"title": source_event["title"]})
            self.assertTrue(actual["is_schedule_exception"], source_event["title"])
            self.assertEqual(actual["schedule_type"], source_event["schedule_type"],
                             source_event["title"])


    def test_e_learning_day_is_remote_learning_not_no_school(self):
        result = classify_event({
            "title": "Election Day - E-Learning Day",
            "description": "MES and MIS will be in session. MJHS will have an E-Learning Day."
        })
        self.assertTrue(result["is_schedule_exception"])
        self.assertEqual(result["schedule_type"], "e_learning")
        self.assertEqual(result["student_attendance"], "remote_learning")

    def test_mokena_sd159_fixture_preserves_school_specific_e_learning(self):
        path = Path(__file__).parents[1] / "data/fixtures/mokena-sd159-2026-27-schedule-exceptions.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(fixture["school_year"], "2026-2027")
        self.assertEqual(len(fixture["events"]), 17)
        election_day = fixture["events"][0]
        self.assertEqual(election_day["start_date"], "2026-11-03")
        self.assertEqual(election_day["school_scope"]["remote_learning"],
                         ["Mokena Junior High School"])
        self.assertEqual(election_day["school_scope"]["in_person"],
                         ["Mokena Elementary School", "Mokena Intermediate School"])
        classified = classify_event({"title": election_day["title"]})
        self.assertEqual(classified["schedule_type"], "e_learning")
        self.assertEqual(classified["student_attendance"], "remote_learning")

    def test_mokena_sd159_fixture_retains_provenance_and_coverage_limits(self):
        path = Path(__file__).parents[1] / "data/fixtures/mokena-sd159-2026-27-schedule-exceptions.json"
        fixture = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(fixture["source"]["coverage_start"], "2026-11-03")
        self.assertEqual(fixture["source"]["vevent_count"], 5936)
        self.assertTrue(all(event["source_event_uids"] for event in fixture["events"]))
        spring_break = next(event for event in fixture["events"]
                            if event["schedule_type"] == "school_break"
                            and event["start_date"] == "2027-03-26")
        self.assertEqual(spring_break["end_date_inclusive"], "2027-04-02")

if __name__ == "__main__":
    unittest.main()
