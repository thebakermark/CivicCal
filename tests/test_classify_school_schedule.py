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


if __name__ == "__main__":
    unittest.main()
