"""Static checks on the group workflows' mode validation wiring."""

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"
GROUPS = ("quality", "build-test", "iac", "security", "dependencies")
MODES = '["audit", "restrict", "advanced"]'


def jobs(name):
    """Split a workflow's jobs section into {job id: job text}."""
    text = (WORKFLOWS / f"{name}.yml").read_text(encoding="utf-8")
    section = text.split("\njobs:\n", 1)[1]
    parts = re.split(
        r"^  ([a-z][a-z0-9-]*):[ \t]*(?:#[^\n]*)?$", section, flags=re.MULTILINE
    )
    return dict(zip(parts[1::2], parts[2::2]))


class GroupModeValidationTests(unittest.TestCase):
    """Every group workflow must reject unknown modes before running checks."""

    def test_groups_validate_mode(self):
        """Each group has a mode job that fails on unsupported values."""
        for group in GROUPS:
            with self.subTest(group=group):
                mode = jobs(group).get("mode", "")
                self.assertIn(f"!contains(fromJSON('{MODES}'), inputs.mode)", mode)
                self.assertIn("exit 1", mode)

    def test_checks_depend_on_mode(self):
        """Every check job waits for mode validation to succeed."""
        for group in GROUPS:
            for job, text in jobs(group).items():
                if job == "mode":
                    continue
                with self.subTest(group=group, job=job):
                    self.assertRegex(text, r"\n    needs: (mode\n|\[mode\b)")
                    condition = re.search(r"\n    if: (.*)", text)
                    # always() overrides needs; such jobs must check mode explicitly.
                    if condition and "always()" in condition.group(1):
                        self.assertIn("needs.mode.result == 'success'", text)


class RunnerSelectionTests(unittest.TestCase):
    """Portable jobs follow the caller while Linux integrations stay isolated."""

    def test_portable_jobs_select_runner(self):
        """Check every selectable job, including direct group callers."""
        groups = {
            "iac": ("terraform", "tflint", "bicep", "cloudformation"),
            "build-test": ("python", "node", "go", "dotnet"),
            "security": (
                "iac-security",
                "codeql-analyze",
                "dependabot",
                "dependency-review",
                "secret-scanning",
            ),
        }
        for group, job_ids in groups.items():
            text = (WORKFLOWS / f"{group}.yml").read_text(encoding="utf-8")
            self.assertRegex(
                text, r"runner:\n(?:[^\n]*\n){2}        default: ubuntu-latest"
            )
            for job_id in job_ids:
                with self.subTest(group=group, job=job_id):
                    self.assertIn("runs-on: ${{ inputs.runner }}", jobs(group)[job_id])

    def test_linux_integrations_remain_on_ubuntu(self):
        """Container-based and Linux-supported checks never follow the runner."""
        for group, job_id in (
            ("quality", "lint"),
            ("build-test", "docker"),
            ("security", "trivy"),
            ("dependencies", "versions"),
        ):
            with self.subTest(group=group, job=job_id):
                self.assertIn("runs-on: ubuntu-latest", jobs(group)[job_id])

    def test_orchestrator_forwards_runner(self):
        """The public input must reach all selectable group workflows."""
        for group in ("iac", "build-test", "security"):
            self.assertIn("runner: ${{ inputs.runner }}", jobs("allinone")[group])

    def test_ci_covers_three_operating_systems(self):
        """Test the reusable workflow and composite action on real runners."""
        for job_id in ("checks", "action"):
            self.assertIn(
                "runner: [ubuntu-latest, macos-latest, windows-latest]",
                jobs("ci")[job_id],
            )

    def test_internal_python_is_independent_of_test_python(self):
        """Caller test versions must not change the reporting/scanning runtime."""
        action = (WORKFLOWS.parents[1] / "action.yml").read_text(encoding="utf-8")
        runtime = action.split("    - name: Set up internal Python tools\n", 1)[1]
        runtime = runtime.split("    - name: Validate runner compatibility\n", 1)[0]
        self.assertIn('python-version: "3.12"', runtime)
        self.assertIn("python-version: ${{ inputs.python-version }}", action)
        self.assertIn(
            "PYTHON_EXECUTABLE: ${{ steps.runtime-python.outputs.python-path }}",
            action,
        )

    def test_controlled_findings_fixture_is_isolated_from_repository_scans(self):
        """Only materialize intentionally insecure IaC in runner-temp."""
        fixture = WORKFLOWS.parents[1] / "tests" / "fixtures" / "checkov"
        self.assertTrue((fixture / "main.tf.fixture").is_file())
        self.assertFalse((fixture / "main.tf").exists())
        action_job = jobs("ci")["action"]
        self.assertIn('mktemp -d "$RUNNER_TEMP/checkov-fixture.XXXXXX"', action_job)
        self.assertIn(
            'cp tests/fixtures/checkov/main.tf.fixture "$fixture/main.tf"', action_job
        )
        self.assertIn("trap 'rm -rf -- \"$fixture\"' EXIT", action_job)


if __name__ == "__main__":
    unittest.main()
