import copy
import unittest

from scripts.validate_snapshot import SnapshotError, attach_snapshot, validate_manifest


class SnapshotValidationTests(unittest.TestCase):
    def profile(self, **overrides):
        value = {
            "source_id": "source-a",
            "profile_id": "test-profile",
            "scope": "A controlled test feed.",
            "pagination_strategy": "single_feed",
            "required_page_roles": ["feed"],
            "require_detail_link_reconciliation": False,
            "allow_complete_snapshot": True,
        }
        value.update(overrides)
        return value

    def page(self, **overrides):
        value = {
            "role": "feed",
            "url": "https://example.test/events.ics",
            "capture_outcome": "captured",
            "http_status": 200,
            "parse_status": "success",
            "content_sha256": "a" * 64,
            "source_event_ids": ["event-1"],
        }
        value.update(overrides)
        return value

    def manifest(self, **overrides):
        value = {
            "format": "civiccal.snapshot-manifest.v1",
            "source_id": "source-a",
            "pagination": {
                "strategy": "single_feed",
                "expected_page_count": 1,
                "observed_page_count": 1,
                "terminal_page_confirmed": True,
                "pending_next_urls": [],
            },
            "pages": [self.page()],
        }
        value.update(overrides)
        return value

    def test_verified_complete_feed_emits_completeness_assertion(self):
        result = validate_manifest(self.manifest(), self.profile())
        self.assertEqual(result["completeness"], "complete")
        self.assertFalse(result["blockers"])
        self.assertIn("test-profile", result["evidence"])

    def test_disabled_source_policy_never_emits_complete(self):
        result = validate_manifest(self.manifest(), self.profile(
            allow_complete_snapshot=False,
            reason_disabled="Live source has not been validated.",
        ))
        self.assertEqual(result["completeness"], "unknown")
        self.assertTrue(result["blockers"])

    def test_missing_page_and_unconfirmed_terminal_page_block_completeness(self):
        manifest = self.manifest()
        manifest["pagination"]["expected_page_count"] = 2
        manifest["pagination"]["observed_page_count"] = 1
        manifest["pagination"]["terminal_page_confirmed"] = False
        manifest["pagination"]["pending_next_urls"] = ["https://example.test/page/2"]
        result = validate_manifest(manifest, self.profile())
        self.assertEqual(result["completeness"], "partial")
        self.assertGreaterEqual(len(result["blockers"]), 3)

    def test_failed_or_unparsed_page_blocks_completeness(self):
        result = validate_manifest(self.manifest(pages=[self.page(
            capture_outcome="failed", http_status=503, parse_status="failed",
        )]), self.profile())
        self.assertEqual(result["completeness"], "partial")
        self.assertTrue(any("not captured successfully" in x for x in result["blockers"]))

    def test_village_detail_pages_must_match_every_discovered_link_id(self):
        profile = self.profile(
            pagination_strategy="rel_next",
            required_page_roles=["listing", "detail"],
            require_detail_link_reconciliation=True,
        )
        manifest = self.manifest(
            pagination={
                "strategy": "rel_next", "expected_page_count": 2,
                "observed_page_count": 2, "terminal_page_confirmed": True,
                "pending_next_urls": [],
            },
            pages=[
                self.page(role="listing", url="https://example.test/calendar",
                          source_event_ids=[], discovered_detail_ids=["cid-1", "cid-2"]),
                self.page(role="detail", url="https://example.test/event?cid=cid-1",
                          source_event_ids=["cid-1"]),
            ],
        )
        result = validate_manifest(manifest, profile)
        self.assertEqual(result["completeness"], "partial")
        self.assertTrue(any("Unparsed linked detail IDs: cid-2" in x for x in result["blockers"]))

    def test_village_completes_only_after_all_detail_ids_are_parsed(self):
        profile = self.profile(
            pagination_strategy="rel_next",
            required_page_roles=["listing", "detail"],
            require_detail_link_reconciliation=True,
        )
        manifest = self.manifest(
            pagination={
                "strategy": "rel_next", "expected_page_count": 3,
                "observed_page_count": 3, "terminal_page_confirmed": True,
                "pending_next_urls": [],
            },
            pages=[
                self.page(role="listing", url="https://example.test/calendar",
                          source_event_ids=[], discovered_detail_ids=["cid-1", "cid-2"]),
                self.page(role="detail", url="https://example.test/event?cid=cid-1",
                          source_event_ids=["cid-1"]),
                self.page(role="detail", url="https://example.test/event?cid=cid-2",
                          source_event_ids=["cid-2"]),
            ],
        )
        result = validate_manifest(manifest, profile)
        self.assertEqual(result["completeness"], "complete")

    def test_empty_snapshot_requires_explicit_confirmation(self):
        manifest = self.manifest(pages=[self.page(source_event_ids=[])])
        result = validate_manifest(manifest, self.profile())
        self.assertEqual(result["completeness"], "partial")
        manifest["empty_snapshot_confirmed"] = True
        result = validate_manifest(manifest, self.profile())
        self.assertEqual(result["completeness"], "complete")
        self.assertTrue(result["empty_snapshot_confirmed"])

    def test_page_host_and_path_must_match_source_allowlist(self):
        profile = self.profile(
            allowed_hosts=["example.test"],
            allowed_paths=["/events.ics"],
        )
        result = validate_manifest(self.manifest(pages=[self.page(
            url="https://other.example/events.ics",
        )]), profile)
        self.assertEqual(result["completeness"], "partial")
        self.assertTrue(any("host is outside" in x for x in result["blockers"]))
        result = validate_manifest(self.manifest(pages=[self.page(
            url="https://example.test/private",
        )]), profile)
        self.assertTrue(any("path is outside" in x for x in result["blockers"]))

    def test_explicitly_confirmed_empty_village_listing_can_be_complete(self):
        profile = self.profile(
            pagination_strategy="rel_next",
            required_page_roles=["listing", "detail"],
            require_detail_link_reconciliation=True,
        )
        manifest = self.manifest(
            empty_snapshot_confirmed=True,
            pagination={
                "strategy": "rel_next", "expected_page_count": 1,
                "observed_page_count": 1, "terminal_page_confirmed": True,
                "pending_next_urls": [],
            },
            pages=[self.page(role="listing", source_event_ids=[], discovered_detail_ids=[])],
        )
        self.assertEqual(validate_manifest(manifest, profile)["completeness"], "complete")

    def test_attach_snapshot_preserves_normalized_document(self):
        normalized = {
            "format": "civiccal.normalized-events.v1",
            "source_id": "source-a",
            "events": [{"source_event_id": "event-1"}],
        }
        policies = {
            "format": "civiccal.source-completeness-policies.v1",
            "profiles": [self.profile()],
        }
        result = attach_snapshot(normalized, self.manifest(), policies)
        self.assertEqual(result["snapshot"]["completeness"], "complete")
        self.assertNotIn("snapshot", normalized)

    def test_source_mismatch_is_rejected(self):
        normalized = {
            "format": "civiccal.normalized-events.v1",
            "source_id": "source-b",
            "events": [],
        }
        policies = {
            "format": "civiccal.source-completeness-policies.v1",
            "profiles": [self.profile()],
        }
        with self.assertRaisesRegex(SnapshotError, "do not match"):
            attach_snapshot(normalized, self.manifest(), policies)


if __name__ == "__main__":
    unittest.main()
