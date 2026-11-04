import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.set_publication import PublicationApprovalError, _atomic_write_json, update_publication


def source_registry(*ids):
    return {"source_records": [{"id": item} for item in ids]}


def event(event_id="evt-a", source_id="village"):
    return {"event_id": event_id, "source_id": source_id, "current": {"title": "Meeting"}}


def state(*records):
    return {
        "format": "civiccal.identity-state.v1",
        "events": {f"key-{index}": record for index, record in enumerate(records)},
    }


def manifest(*ids):
    return {"format": "civiccal.publication-manifest.v1", "calendar_name": "Village", "approved_event_ids": list(ids)}


class SetPublicationTests(unittest.TestCase):
    def test_approve_adds_only_requested_event(self):
        updated, summary = update_publication(
            source_registry("village"), state(event(), event("evt-b")),
            manifest("evt-b"), "village", "evt-a", "approve",
        )
        self.assertEqual(updated["approved_event_ids"], ["evt-b", "evt-a"])
        self.assertTrue(summary["currently_approved"])
        self.assertTrue(summary["changed"])

    def test_revoke_removes_only_requested_event(self):
        updated, summary = update_publication(
            source_registry("village"), state(event(), event("evt-b")),
            manifest("evt-a", "evt-b"), "village", "evt-a", "revoke",
        )
        self.assertEqual(updated["approved_event_ids"], ["evt-b"])
        self.assertFalse(summary["currently_approved"])

    def test_approve_and_revoke_are_idempotent(self):
        current = manifest("evt-a")
        approved, result = update_publication(
            source_registry("village"), state(event()), current, "village", "evt-a", "approve"
        )
        self.assertFalse(result["changed"])
        revoked, result = update_publication(
            source_registry("village"), state(event()), approved, "village", "evt-a", "revoke"
        )
        self.assertTrue(result["changed"])
        unchanged, result = update_publication(
            source_registry("village"), state(event()), revoked, "village", "evt-a", "revoke"
        )
        self.assertFalse(result["changed"])
        self.assertEqual(unchanged["approved_event_ids"], [])

    def test_rejects_event_owned_by_another_source(self):
        with self.assertRaisesRegex(PublicationApprovalError, "belongs to source"):
            update_publication(
                source_registry("village", "library"), state(event(source_id="library")),
                manifest(), "village", "evt-a", "approve",
            )

    def test_rejects_unknown_or_ambiguous_registered_source(self):
        with self.assertRaisesRegex(PublicationApprovalError, "exactly one registered source"):
            update_publication(source_registry("library"), state(event()), manifest(),
                               "village", "evt-a", "approve")
        with self.assertRaisesRegex(PublicationApprovalError, "exactly one registered source"):
            update_publication(source_registry("village", "village"), state(event()), manifest(),
                               "village", "evt-a", "approve")

    def test_rejects_unknown_event_and_duplicate_identity(self):
        with self.assertRaisesRegex(PublicationApprovalError, "exactly one stored event"):
            update_publication(source_registry("village"), state(event()), manifest(),
                               "village", "missing", "approve")
        with self.assertRaisesRegex(PublicationApprovalError, "duplicate event ID"):
            update_publication(source_registry("village"), state(event(), event()),
                               manifest(), "village", "evt-a", "approve")

    def test_rejects_malformed_manifest(self):
        invalid = {"format": "civiccal.publication-manifest.v1", "approved_event_ids": ["evt-a", "evt-a"]}
        with self.assertRaisesRegex(PublicationApprovalError, "duplicate event IDs"):
            update_publication(source_registry("village"), state(event()), invalid,
                               "village", "evt-a", "approve")

    def test_cli_approves_event_and_changes_only_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry_path = root / "sources.json"
            state_path = root / "identity.json"
            manifest_path = root / "publication.json"
            registry = source_registry("village")
            identity = state(event())
            publication = manifest()
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            state_path.write_text(json.dumps(identity), encoding="utf-8")
            manifest_path.write_text(json.dumps(publication), encoding="utf-8")

            command = [
                sys.executable, str(Path(__file__).resolve().parents[1] / "scripts" / "set_publication.py"),
                "--registry", str(registry_path),
                "--identity-state", str(state_path),
                "--manifest", str(manifest_path),
                "--source-id", "village",
                "--event-id", "evt-a",
                "--action", "approve",
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["currently_approved"])
            self.assertEqual(json.loads(manifest_path.read_text(encoding="utf-8"))["approved_event_ids"], ["evt-a"])
            self.assertEqual(json.loads(registry_path.read_text(encoding="utf-8")), registry)
            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), identity)

    def test_rejects_manifest_approvals_missing_from_identity_state(self):
        with self.assertRaisesRegex(PublicationApprovalError, "missing from identity state"):
            update_publication(source_registry("village"), state(event()), manifest("evt-missing"),
                               "village", "evt-a", "approve")

    def test_rejects_existing_approval_with_unregistered_source(self):
        with self.assertRaisesRegex(PublicationApprovalError, "exactly one registered source"):
            update_publication(source_registry("village"), state(event(), event("evt-b", "retired-source")),
                               manifest("evt-b"), "village", "evt-a", "approve")

    def test_atomic_writer_preserves_complete_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "publication.json"
            _atomic_write_json(path, manifest("evt-a"))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), manifest("evt-a"))
            self.assertFalse(list(Path(directory).glob("*.tmp")))


if __name__ == "__main__":
    unittest.main()
