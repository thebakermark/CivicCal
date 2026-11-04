import copy
import unittest

from scripts.track_event_identity import (
    IdentityError, process_normalized,
)


def normalized(events, source="source-a", capture="capture-1"):
    return {
        "format": "civiccal.normalized-events.v1",
        "source_id": source,
        "capture": {"content_sha256": capture},
        "events": events,
    }


def event(uid="publisher-1", title="Town meeting", **overrides):
    value = {
        "source_event_id": uid,
        "title": title,
        "description": "Public meeting",
        "start": {"value": "2026-11-04T18:00", "kind": "date-time",
                  "timezone": "America/Chicago", "utc_offset": None},
        "end": None,
        "all_day": False,
        "time_status": "zoned",
        "timezone": "America/Chicago",
        "location": {"name": "Village Hall"},
        "event_url": "https://example.test/event/1",
        "registration_url": None,
        "registration_deadline": None,
        "cost_text": None,
        "is_free": None,
        "status": "scheduled",
        "attendance_mode": None,
        "audience": None,
        "organizer": None,
        "image_url": None,
        "categories": [],
        "recurrence": None,
        "data_quality_flags": [],
        "source_record": {"uid": uid, "title": title},
        "capture": None,
    }
    value.update(overrides)
    return value


class TrackEventIdentityTests(unittest.TestCase):
    def test_first_observation_creates_stable_source_scoped_id_and_revision(self):
        result, state = process_normalized(normalized([event()]), observed_at="2026-11-04T12:00:00Z")
        self.assertEqual(result["new_events"], 1)
        self.assertEqual(result["new_revisions"], 0)
        self.assertEqual(len(state["events"]), 1)
        current = next(iter(state["events"].values()))
        self.assertTrue(current["event_id"].startswith("evt_"))
        self.assertEqual(current["revisions"][0]["revision"], 1)
        self.assertEqual(current["revisions"][0]["change_type"], "created")

    def test_same_source_uid_updated_title_creates_revision_same_event_id(self):
        first, state = process_normalized(normalized([event()], capture="capture-1"))
        event_id = first["events"][0]["event_id"]
        second, state = process_normalized(
            normalized([event(title="Updated meeting")], capture="capture-2"),
            state, observed_at="2026-11-04T13:00:00Z")
        self.assertEqual(second["new_events"], 0)
        self.assertEqual(second["new_revisions"], 1)
        current = next(iter(state["events"].values()))
        self.assertEqual(current["event_id"], event_id)
        self.assertEqual(len(current["revisions"]), 2)
        self.assertEqual(current["current"]["title"], "Updated meeting")

    def test_identical_new_capture_is_unchanged_not_revision(self):
        _, state = process_normalized(normalized([event()], capture="capture-1"))
        result, state = process_normalized(normalized([event()], capture="capture-2"), state)
        self.assertEqual(result["unchanged_events"], 1)
        self.assertEqual(result["new_revisions"], 0)
        self.assertEqual(len(next(iter(state["events"].values()))["revisions"]), 1)

    def test_reprocessing_same_capture_is_idempotent(self):
        document = normalized([event()], capture="capture-1")
        first, state = process_normalized(document)
        second, state2 = process_normalized(document, state)
        self.assertTrue(second["already_processed"])
        self.assertEqual(state, state2)

    def test_source_scope_prevents_cross_source_identity_collision(self):
        _, state = process_normalized(normalized([event()], source="source-a", capture="a"))
        result, state = process_normalized(normalized([event()], source="source-b", capture="b"), state)
        self.assertEqual(result["new_events"], 1)
        self.assertEqual(len(state["events"]), 2)

    def test_every_capture_is_retained_as_source_observation(self):
        _, state = process_normalized(normalized([event()], capture="capture-1"),
                                      observed_at="2026-11-04T12:00:00Z")
        result, state = process_normalized(normalized([event()], capture="capture-2"),
                                            state, observed_at="2026-11-04T13:00:00Z")
        self.assertEqual(result["unchanged_events"], 1)
        self.assertEqual(len(state["observations"]), 2)
        self.assertEqual(state["observations"][0]["event"]["title"], "Town meeting")
        self.assertEqual(state["observations"][1]["capture_key"], "capture-2")
        self.assertEqual(len(next(iter(state["events"].values()))["revisions"]), 1)

    def test_explicit_source_cancellation_is_lifecycle_transition(self):
        _, state = process_normalized(normalized([event()], capture="capture-1"))
        result, state = process_normalized(
            normalized([event(status="cancelled")], capture="capture-2"), state,
            observed_at="2026-11-04T14:00:00Z")
        current = next(iter(state["events"].values()))
        self.assertEqual(result["new_revisions"], 1)
        self.assertEqual(current["lifecycle_status"], "cancelled")
        self.assertEqual(current["lifecycle_history"][-1]["transition"],
                         "explicit_source_status_change")
        self.assertEqual(current["lifecycle_history"][-1]["from_status"], "scheduled")
        self.assertEqual(current["lifecycle_history"][-1]["to_status"], "cancelled")

    def test_missing_source_id_is_unkeyed_and_retained(self):
        value = event(uid=None)
        result, state = process_normalized(normalized([value]))
        self.assertEqual(result["unkeyed_count"], 1)
        self.assertEqual(len(state["unkeyed_observations"]), 1)
        self.assertEqual(len(state["events"]), 0)
        self.assertIn("stable_source_event_id_missing", result["unkeyed_observations"][0]["review_flags"])

    def test_duplicate_source_identity_in_same_capture_is_conflict_not_overwrite(self):
        result, state = process_normalized(normalized([event(), event(title="Different")]))
        self.assertEqual(len(result["identity_conflicts"]), 1)
        self.assertEqual(result["new_events"], 0)
        self.assertEqual(len(state["events"]), 0)

    def test_recurrence_instances_get_distinct_stable_ids(self):
        a = event(recurrence={"instance_id": "20261104T180000"})
        b = event(recurrence={"instance_id": "20261111T180000"})
        result, state = process_normalized(normalized([a, b]))
        self.assertEqual(result["new_events"], 2)
        self.assertEqual(len(state["events"]), 2)

    def test_missing_from_later_capture_does_not_cancel_or_delete(self):
        _, state = process_normalized(normalized([event()], capture="capture-1"))
        result, state = process_normalized(normalized([], capture="capture-2"), state)
        current = next(iter(state["events"].values()))
        self.assertEqual(current["current"]["status"], "scheduled")
        self.assertEqual(len(state["events"]), 1)
        self.assertEqual(result["new_events"], 0)

    def test_nonmaterial_source_record_change_does_not_create_revision(self):
        original = event()
        _, state = process_normalized(normalized([original], capture="capture-1"))
        changed_source_record = event()
        changed_source_record["source_record"] = {"uid": "publisher-1", "fetched_label": "new"}
        result, state = process_normalized(
            normalized([changed_source_record], capture="capture-2"), state)
        self.assertEqual(result["unchanged_events"], 1)
        self.assertEqual(result["new_revisions"], 0)

    def test_invalid_normalized_input_rejected(self):
        with self.assertRaises(IdentityError):
            process_normalized({"format": "wrong", "source_id": "x", "events": []})

    def test_input_not_mutated(self):
        document = normalized([event()])
        original = copy.deepcopy(document)
        process_normalized(document)
        self.assertEqual(document, original)


if __name__ == "__main__":
    unittest.main()
