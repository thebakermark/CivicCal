import unittest

from scripts.find_duplicate_candidates import find_duplicate_candidates, signature_for


def event(uid, source="source-a", **overrides):
    value = {
        "uid": uid,
        "source_id": source,
        "title": "School Holiday",
        "description": "No school",
        "location": "Mokena, IL",
        "start": {"value": "2027-12-24", "kind": "date", "timezone": None, "utc": False},
        "end": {"value": "2027-12-25", "kind": "date", "timezone": None, "utc": False},
        "status": "CONFIRMED",
    }
    value.update(overrides)
    return value


class DuplicateCandidateTests(unittest.TestCase):
    def test_different_uids_same_content_are_candidates(self):
        result = find_duplicate_candidates({"events": [event("one"), event("two", "another-source")]})
        self.assertEqual(result["candidate_group_count"], 1)
        self.assertEqual(result["candidate_record_count"], 2)
        self.assertEqual(result["excess_record_count"], 1)
        self.assertEqual(len(result["groups"][0]["records"]), 2)

    def test_whitespace_and_case_differences_normalize(self):
        result = find_duplicate_candidates({
            "events": [
                event("one"),
                event("two", title="  SCHOOL   HOLIDAY ", description="NO   SCHOOL", location="mokena, il"),
            ]
        })
        self.assertEqual(result["candidate_group_count"], 1)

    def test_different_dates_are_not_candidates(self):
        result = find_duplicate_candidates({
            "events": [event("one"), event("two", start={"value": "2027-12-25", "kind": "date", "timezone": None, "utc": False})]
        })
        self.assertEqual(result["candidate_group_count"], 0)

    def test_different_descriptions_are_not_candidates(self):
        result = find_duplicate_candidates({"events": [event("one"), event("two", description="Early dismissal")]})
        self.assertEqual(result["candidate_group_count"], 0)

    def test_different_statuses_are_not_candidates(self):
        result = find_duplicate_candidates({"events": [event("one"), event("two", status="CANCELLED")]})
        self.assertEqual(result["candidate_group_count"], 0)

    def test_events_without_title_or_start_are_skipped(self):
        result = find_duplicate_candidates({"events": [event("one", title=None), event("two", start=None)]})
        self.assertEqual(result["candidate_group_count"], 0)
        self.assertEqual(result["source_event_count"], 2)

    def test_signature_excludes_uid_and_source(self):
        self.assertEqual(signature_for(event("one", "a")), signature_for(event("two", "b")))


if __name__ == "__main__":
    unittest.main()
