"""Tests for report conversion and summary policy scripts."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".github" / "scripts"


def run_script(name, values):
    """Run a report script with an isolated environment."""
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
    """Verify composite-action step outcomes become group results."""

    def run_converter(self, steps):
        """Convert fabricated step outcomes to JSON results."""
        result = run_script("action-results.py", {"STEPS": json.dumps(steps)})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_platform_and_runtime_failures_are_configuration_errors(self):
        """Unsupported runners and missing Python must never look successful."""
        for step in ("platform", "runtime-python"):
            with self.subTest(step=step):
                results = self.run_converter({step: {"outcome": "failure"}})
                self.assertEqual(results["configuration"]["result"], "failure")

    def test_internal_python_setup_does_not_enable_python_check(self):
        """Provisioning reporting tools does not count as running Python tests."""
        results = self.run_converter({"runtime-python": {"outcome": "success"}})
        self.assertEqual(results["build-test"]["outputs"]["python"], "")

    def test_maps_failed_setup_and_skipped_check(self):
        """Map failed setup and skipped steps to stable results."""
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
        """Aggregate multiple step outcomes with failure precedence."""
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
        """Reject malformed serialized action step outcomes."""
        result = run_script("action-results.py", {"STEPS": "{"})
        self.assertNotEqual(result.returncode, 0)


class SummaryTests(unittest.TestCase):
    """Verify result summaries and mode-specific exit policies."""

    def run_summary(self, results, mode):
        """Run summarize.py with temporary summary output."""
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
        """Report but tolerate failed checks in non-restrict modes."""
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
        """Fail in restrict mode and retain skipped results in Markdown."""
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
        """Report a group-level failure if it has no check outputs."""
        results = {
            "configuration": {"result": "success"},
            "security": {"result": "failure", "outputs": {}},
        }
        result, summary = self.run_summary(results, "audit")
        self.assertEqual(result.returncode, 0)
        self.assertIn("| security | (workflow) |", summary)

    def test_invalid_configuration_fails_before_checks(self):
        """Fail summary generation when configuration is invalid."""
        results = {
            "configuration": {"result": "failure"},
            "quality": {"result": "skipped", "outputs": {}},
        }
        result, summary = self.run_summary(results, "audit")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Invalid configuration", summary)

    def test_missing_or_malformed_results_fail(self):
        """Reject absent and malformed serialized workflow results."""
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
    """Verify per-language CodeQL results and failure handling."""

    def run_converter(self, languages, results):
        """Convert fabricated language results and capture the summary."""
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
        """Succeed when every requested CodeQL language succeeds."""
        result, summary = self.run_converter(
            ["python", "go"], {"python": "success", "go": "success"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("| python | success |", summary)
        self.assertIn("| go | success |", summary)

    def test_missing_or_failed_language_fails(self):
        """Fail if a CodeQL language fails or has no result."""
        for results in ({"python": "success"}, {"python": "failure", "go": "success"}):
            with self.subTest(results=results):
                result, summary = self.run_converter(["python", "go"], results)
                self.assertEqual(result.returncode, 1)
                self.assertIn("One or more CodeQL analyses", result.stdout)
                self.assertIn("| go |", summary)

    def test_empty_or_malformed_data_fails(self):
        """Reject empty language selections and malformed JSON."""
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
    """Verify dependency update and lookup-error reporting."""

    def run_report(self, lines):
        """Run renovate-report.py with a temporary JSONL report."""
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
        """List available package updates and return a failing status."""
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
        """Pass clean lookups and fail when a lookup has errors."""
        empty = {"msg": "packageFiles with updates", "config": {}}
        result, summary = self.run_report(json.dumps(empty) + "\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("No supported dependency updates", summary)

        error = {"level": 50, "msg": "lookup failed"}
        result, summary = self.run_report(json.dumps(error) + "\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("lookup failed", summary)

    def test_missing_and_malformed_reports_fail(self):
        """Fail when the report is missing or contains malformed JSON."""
        result, summary = self.run_report(None)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Renovate lookup produced no report", result.stdout)
        self.assertIn("lookup failed before writing a report", summary)

        result, _ = self.run_report("not-json\n")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
