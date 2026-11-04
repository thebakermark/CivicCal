import json
import tempfile
import unittest
from pathlib import Path

from scripts.storage import JsonFileIdentityStateStore


class JsonFileIdentityStateStoreTests(unittest.TestCase):
    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JsonFileIdentityStateStore(Path(directory) / "state.json")
            self.assertIsNone(store.load_identity_state())

    def test_save_creates_parent_and_round_trips_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "state.json"
            store = JsonFileIdentityStateStore(path)
            expected = {"format": "civiccal.identity-state.v1",
                        "events": {"a": {"title": "Parade 🎈"}},
                        "unkeyed_observations": [], "processed_captures": []}
            store.save_identity_state(expected)
            self.assertEqual(store.load_identity_state(), expected)
            self.assertTrue(path.read_text(encoding="utf-8").endswith("\n"))

    def test_save_replaces_existing_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JsonFileIdentityStateStore(Path(directory) / "state.json")
            store.save_identity_state({"version": 1})
            store.save_identity_state({"version": 2})
            self.assertEqual(store.load_identity_state(), {"version": 2})

    def test_invalid_json_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("{broken", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                JsonFileIdentityStateStore(path).load_identity_state()

    def test_non_object_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                JsonFileIdentityStateStore(path).load_identity_state()


if __name__ == "__main__":
    unittest.main()
