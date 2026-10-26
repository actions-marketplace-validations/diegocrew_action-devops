"""Tests for report conversion and summary policy scripts."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".github" / "scripts"


def run_script(name, values):
    env = os.environ.copy()
    env.update({key: str(value) for key, value in values.items()})
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name)],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )


class ActionResultsTests(unittest.TestCase):
    def run_converter(self, steps):
        result = run_script("action-results.py", {"STEPS": json.dumps(steps)})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_maps_failed_setup_and_skipped_check(self):
        results = self.run_converter(
            {
                "python-setup": {"outcome": "failure"},
                "python": {"outcome": "skipped"},
                "lint": {"outcome": "success"},
            }
        )
        self.assertEqual(results["build-test"]["outputs"]["python"], "failure")
        self.assertEqual(results["quality"]["outputs"]["lint"], "success")
        self.assertEqual(results["iac"]["outputs"]["terraform"], "")

    def test_failure_takes_precedence_over_success_and_cancelled(self):
        results = self.run_converter(
            {
                "versions-lookup": {"outcome": "success"},
                "versions": {"outcome": "cancelled"},
                "codeql-analyze": {"outcome": "failure"},
                "codeql-init": {"outcome": "success"},
            }
        )
        self.assertEqual(results["dependencies"]["outputs"]["versions"], "cancelled")
        self.assertEqual(results["security"]["outputs"]["codeql"], "failure")

    def test_malformed_steps_json_fails(self):
        result = run_script("action-results.py", {"STEPS": "{"})
        self.assertNotEqual(result.returncode, 0)


class SummaryTests(unittest.TestCase):
    def run_summary(self, results, mode):
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "summary.md"
            values = {"GITHUB_STEP_SUMMARY": summary_path, "MODE": mode}
            if results is not None:
                values["RESULTS"] = json.dumps(results)
            result = run_script("summarize.py", values)
            summary = (
                summary_path.read_text(encoding="utf-8")
                if summary_path.exists()
                else ""
            )
        return result, summary

    def test_audit_and_advanced_tolerate_check_failures(self):
        results = {
            "configuration": {"result": "success"},
            "quality": {
                "result": "failure",
                "outputs": {"lint": "failure", "disabled": ""},
            },
        }
        for mode in ("audit", "advanced"):
            with self.subTest(mode=mode):
                result, summary = self.run_summary(results, mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"tolerated in {mode} mode", summary)
                self.assertIn("**1 failed:** quality/lint", summary)

    def test_restrict_fails_and_reports_skipped_checks(self):
        results = {
            "configuration": {"result": "success"},
            "quality": {
                "result": "failure",
                "outputs": {"lint": "failure", "disabled": ""},
            },
        }
        result, summary = self.run_summary(results, "restrict")
        self.assertEqual(result.returncode, 1)
        self.assertIn("| quality | disabled | skipped |", summary)
        self.assertIn("**1 failed:** quality/lint", summary)
        self.assertIn("**failure**", summary)

    def test_failed_group_without_check_outputs_is_reported(self):
        results = {
            "configuration": {"result": "success"},
            "security": {"result": "failure", "outputs": {}},
        }
        result, summary = self.run_summary(results, "audit")
        self.assertEqual(result.returncode, 0)
        self.assertIn("| security | (workflow) |", summary)

    def test_invalid_configuration_fails_before_checks(self):
        results = {
            "configuration": {"result": "failure"},
            "quality": {"result": "skipped", "outputs": {}},
        }
        result, summary = self.run_summary(results, "audit")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid configuration", summary)

    def test_missing_or_malformed_results_fail(self):
        result, _ = self.run_summary(None, "audit")
        self.assertNotEqual(result.returncode, 0)

        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "summary.md"
            result = run_script(
                "summarize.py",
                {
                    "RESULTS": "not-json",
                    "MODE": "audit",
                    "GITHUB_STEP_SUMMARY": summary_path,
                },
            )
        self.assertNotEqual(result.returncode, 0)


class CodeQLResultsTests(unittest.TestCase):
    def run_converter(self, languages, results):
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "summary.md"
            result = run_script(
                "codeql-results.py",
                {
                    "LANGUAGES": json.dumps(languages),
                    "RESULTS": json.dumps(results),
                    "GITHUB_STEP_SUMMARY": summary_path,
                },
            )
            summary = summary_path.read_text(encoding="utf-8")
        return result, summary

    def test_all_languages_must_succeed(self):
        result, summary = self.run_converter(
            ["python", "go"], {"python": "success", "go": "success"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("| python | success |", summary)
        self.assertIn("| go | success |", summary)

    def test_missing_or_failed_language_fails(self):
        for results in ({"python": "success"}, {"python": "failure", "go": "success"}):
            with self.subTest(results=results):
                result, summary = self.run_converter(["python", "go"], results)
                self.assertEqual(result.returncode, 1)
                self.assertIn("One or more CodeQL analyses", result.stdout)
                self.assertIn("| go |", summary)

    def test_empty_or_malformed_data_fails(self):
        for languages in ([], "not-json"):
            with self.subTest(languages=languages):
                result, _ = self.run_converter(languages, {})
                self.assertNotEqual(result.returncode, 0)

        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "summary.md"
            result = run_script(
                "codeql-results.py",
                {
                    "LANGUAGES": '["python"]',
                    "RESULTS": "not-json",
                    "GITHUB_STEP_SUMMARY": summary_path,
                },
            )
        self.assertNotEqual(result.returncode, 0)


class RenovateReportTests(unittest.TestCase):
    def run_report(self, lines):
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "renovate.json"
            summary_path = Path(directory) / "summary.md"
            if lines is not None:
                report_path.write_text(lines, encoding="utf-8")
            result = run_script(
                "renovate-report.py",
                {"REPORT": report_path, "GITHUB_STEP_SUMMARY": summary_path},
            )
            summary = (
                summary_path.read_text(encoding="utf-8")
                if summary_path.exists()
                else ""
            )
        return result, summary

    def test_updates_are_summarized_and_fail_the_check(self):
        record = {
            "msg": "packageFiles with updates",
            "config": {
                "npm": [
                    {
                        "packageFile": "package.json",
                        "deps": [
                            {
                                "depName": "sample",
                                "currentValue": "1.0.0",
                                "updates": [{"newVersion": "1.1.0"}],
                            }
                        ],
                    }
                ]
            },
        }
        result, summary = self.run_report(json.dumps(record) + "\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("package.json: sample 1.0.0 -> 1.1.0", summary)

    def test_no_updates_passes_and_lookup_errors_fail(self):
        empty = {"msg": "packageFiles with updates", "config": {}}
        result, summary = self.run_report(json.dumps(empty) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No supported dependency updates", summary)

        error = {"level": 50, "msg": "lookup failed"}
        result, summary = self.run_report(json.dumps(error) + "\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("lookup failed", summary)

    def test_missing_and_malformed_reports_fail(self):
        for lines in (None, "not-json\n"):
            with self.subTest(lines=lines):
                result, _ = self.run_report(lines)
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()