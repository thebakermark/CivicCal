import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_capture_job import run_job, safe_source_id


class CaptureJobRunnerTests(unittest.TestCase):
    def test_source_id_is_restricted_for_safe_paths_and_systemd_instance(self):
        self.assertEqual(safe_source_id("mokena-sd159-events-ical"), "mokena-sd159-events-ical")
        for invalid in ("../etc/passwd", "UpperCase", "has space", "a/b", ""):
            with self.subTest(invalid=invalid), self.assertRaises(Exception):
                safe_source_id(invalid)

    def test_runner_writes_report_without_mutating_registry(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            registry = root / "sources.json"
            registry.write_text(json.dumps({
                "source_records": [{
                    "id": "example-school-ical",
                    "source_type": "ics",
                    "url": "https://calendar.example.test/events.ics",
                    "access_status": "approved",
                    "terms_reviewed": True,
                    "robots_reviewed": True,
                    "consent_required": False,
                    "polling_enabled": False,
                }]
            }), encoding="utf-8")
            before = registry.read_bytes()
            policies = root / "policies.json"
            policies.write_text("{}", encoding="utf-8")
            expected = {
                "event_count": 3,
                "summary": {"parser_warning_count": 0},
                "snapshot": {"completeness": "unknown"},
                "events": [],
            }
            with patch("scripts.run_capture_job.coordinate_ics_capture", return_value=expected) as capture:
                report_path, result = run_job(
                    "example-school-ical", registry=registry, policies=policies,
                    archive_dir=root / "captures", reports_dir=root / "reports",
                )
            self.assertEqual(result, expected)
            self.assertTrue(report_path.is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["format"], "civiccal.capture-job-report.v1")
            self.assertFalse(report["job"]["automatic_polling_enabled"])
            self.assertFalse(report["job"]["published"])
            self.assertFalse(report["job"]["source_registry_modified"])
            capture.assert_called_once()
            self.assertEqual(registry.read_bytes(), before)

    def test_invalid_timeout_is_rejected_before_registry_access(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "timeout"):
                run_job(
                    "example-school-ical", registry=root / "missing.json",
                    policies=root / "policies.json", archive_dir=root / "captures",
                    reports_dir=root / "reports", timeout=0,
                )


if __name__ == "__main__":
    unittest.main()
