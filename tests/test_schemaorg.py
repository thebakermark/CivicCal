import copy
import unittest

from scripts.schemaorg import to_schemaorg_event


class SchemaOrgProjectionTests(unittest.TestCase):
    def test_maps_supported_event_fields(self):
        event = {
            "source_id": "school-calendar",
            "source_event_id": "publisher-123",
            "title": "Winter Concert",
            "description": "Student performances.",
            "start": {"value": "2026-12-10T18:30:00", "kind": "date-time",
                      "timezone": "America/Chicago"},
            "end": {"value": "2026-12-10T20:00:00", "kind": "date-time",
                    "timezone": "America/Chicago"},
            "location": {"name": "Auditorium", "address": "123 Main Street"},
            "event_url": "https://example.org/events/123",
            "registration_url": "https://example.org/register/123",
            "organizer": {"name": "Example School", "url": "https://example.org"},
            "status": "scheduled",
            "attendance_mode": "offline",
            "is_free": True,
            "audience": ["Students", "Families"],
            "categories": ["Music", "Concert"],
        }
        result = to_schemaorg_event(event)
        self.assertEqual(result["@type"], "Event")
        self.assertEqual(result["name"], "Winter Concert")
        self.assertEqual(result["startDate"], "2026-12-10T18:30:00")
        self.assertEqual(result["endDate"], "2026-12-10T20:00:00")
        self.assertEqual(result["location"]["@type"], "Place")
        self.assertEqual(result["organizer"]["@type"], "Organization")
        self.assertEqual(result["eventStatus"], "https://schema.org/EventScheduled")
        self.assertEqual(result["eventAttendanceMode"],
                         "https://schema.org/OfflineEventAttendanceMode")
        self.assertTrue(result["isAccessibleForFree"])
        self.assertEqual(result["keywords"], ["Music", "Concert"])
        self.assertEqual(result["identifier"], "publisher-123")
        self.assertEqual(result["potentialAction"]["@type"], "RegisterAction")
        self.assertNotIn("source_id", result)

    def test_date_only_remains_date_only(self):
        result = to_schemaorg_event({
            "title": "Holiday",
            "start": {"value": "2026-12-25", "kind": "date"},
            "all_day": True,
        })
        self.assertEqual(result["startDate"], "2026-12-25")
        self.assertNotIn("endDate", result)

    def test_floating_datetime_does_not_gain_timezone(self):
        result = to_schemaorg_event({
            "title": "Meeting",
            "start": {"value": "2026-12-01T18:00:00", "kind": "date-time",
                      "timezone": None},
        })
        self.assertEqual(result["startDate"], "2026-12-01T18:00:00")
        self.assertNotIn("timezone", result)

    def test_unparsed_temporal_value_is_omitted(self):
        result = to_schemaorg_event({
            "title": "Unresolved",
            "start": {"value": "next Thursday", "kind": "unparsed"},
        })
        self.assertNotIn("startDate", result)

    def test_unknown_status_and_attendance_are_omitted(self):
        result = to_schemaorg_event({
            "title": "Event",
            "status": "unknown",
            "attendance_mode": "hybrid-ish",
        })
        self.assertNotIn("eventStatus", result)
        self.assertNotIn("eventAttendanceMode", result)

    def test_false_free_value_is_preserved(self):
        result = to_schemaorg_event({"title": "Fundraiser", "is_free": False})
        self.assertIs(result["isAccessibleForFree"], False)

    def test_empty_and_malformed_optional_fields_are_omitted(self):
        result = to_schemaorg_event({
            "title": "  Event  ",
            "description": "",
            "location": {"address": None},
            "categories": [" ", None, 7],
            "audience": [],
            "organizer": {},
            "registration_url": "",
        })
        self.assertEqual(result["name"], "Event")
        self.assertNotIn("description", result)
        self.assertNotIn("location", result)
        self.assertNotIn("keywords", result)
        self.assertNotIn("audience", result)
        self.assertNotIn("organizer", result)
        self.assertNotIn("potentialAction", result)

    def test_projection_does_not_mutate_normalized_event(self):
        event = {"title": "Event", "categories": ["Music"],
                 "audience": ["Families"]}
        original = copy.deepcopy(event)
        to_schemaorg_event(event)
        self.assertEqual(event, original)

    def test_non_object_is_rejected(self):
        with self.assertRaises(TypeError):
            to_schemaorg_event("not an event")


if __name__ == "__main__":
    unittest.main()
