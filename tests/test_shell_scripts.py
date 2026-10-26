"""Fixture tests for Bash scripts; external tools are replaced with stubs."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / ".github" / "scripts"
BASH = shutil.which("bash")


@unittest.skipUnless(os.name == "posix" and BASH, "requires a POSIX Bash runner")
class ShellScriptTests(unittest.TestCase):
    """Exercise Bash scripts with temporary fixtures and mocked tools."""

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        self.scripts = self.root / "scripts"
        self.scripts.mkdir()
        for source in SCRIPTS.glob("*.sh"):
            (self.scripts / source.name).write_text(
                source.read_text(encoding="utf-8"), encoding="utf-8"
            )
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.runner_temp = self.root / "runner-temp"
        self.runner_temp.mkdir()
        self.summary = self.root / "summary.md"
        self.log = self.root / "tool.log"

    def _environment(self, **values):
        """Build an environment isolated to this fixture directory."""
        env = os.environ.copy()
        env.update(
            {
                "PATH": os.pathsep.join((str(self.bin), env.get("PATH", ""))),
                "RUNNER_TEMP": str(self.runner_temp),
                "GITHUB_STEP_SUMMARY": str(self.summary),
                "TOOL_LOG": str(self.log),
            }
        )
        env.update({key: str(value) for key, value in values.items()})
        return env

    def _run_script(self, name, *args, cwd=None, **values):
        """Run one script from the LF-normalized fixture copy."""
        return subprocess.run(
            [BASH, str(self.scripts / name), *args],
            check=False,
            capture_output=True,
            cwd=cwd or self.root,
            env=self._environment(**values),
            text=True,
        )

    def _executable(self, name, body):
        """Install an executable stub on the fixture PATH."""
        path = self.bin / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_validate_config_accepts_modes_and_rejects_typos(self):
        """Allow supported modes and reject invalid values."""
        for mode in ("audit", "restrict", "advanced"):
            with self.subTest(mode=mode):
                result = self._run_script("validate-config.sh", MODE=mode)
                self.assertEqual(result.returncode, 0, result.stderr)

        result = self._run_script("validate-config.sh", MODE="restrcit")
        self.assertEqual(result.returncode, 1)
        self.assertIn("mode must be", result.stdout)

    def test_codeql_language_list_is_normalized_and_classified(self):
        """Normalize selected languages and classify the build mode."""
        result = self._run_script(
            "codeql-language.sh",
            CODEQL_LANGUAGE="python, python\ngo",
            GITHUB_OUTPUT=self.root / "outputs.txt",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = (self.root / "outputs.txt").read_text(encoding="utf-8")
        self.assertIn('languages=["python","go"]', output)
        self.assertIn("build-mode=mixed", output)

    def test_codeql_language_rejects_empty_and_unsupported_values(self):
        """Reject empty and unsupported CodeQL language names."""
        for language in ("", "swift"):
            with self.subTest(language=language):
                result = self._run_script(
                    "codeql-language.sh",
                    CODEQL_LANGUAGE=language,
                    GITHUB_OUTPUT=self.root / "outputs.txt",
                )
                self.assertEqual(result.returncode, 1)

    def test_split_list_trims_and_skips_empty_items(self):
        """Trim each list item and discard empty entries."""
        helper = self.scripts / "list.sh"
        result = subprocess.run(
            [
                BASH,
                "-c",
                'source "$1"; split_list "$2"',
                "bash",
                str(helper),
                " a, b\n\nc ",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["a", "b", "c"])

    def _install_terraform_stub(self):
        """Stub Terraform and allow a selected root to fail validation."""
        self._executable(
            "terraform",
            "#!/usr/bin/env bash\n"
            'printf "%s|%s\\n" "${PWD##*/}" "$*" >>"$TOOL_LOG"\n'
            'if [[ "${FAIL_ROOT:-}" == "${PWD##*/}" && "$1" == validate ]]; then\n'
            "  exit 7\n"
            "fi\n",
        )

    def test_terraform_checks_every_root_and_continues_after_failure(self):
        """Continue across roots and summarize every Terraform result."""
        self._install_terraform_stub()
        (self.root / "one").mkdir()
        (self.root / "two").mkdir()
        result = self._run_script(
            "terraform-validate.sh", TF_DIRECTORY="one,two", FAIL_ROOT="one"
        )
        self.assertEqual(result.returncode, 1)
        calls = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(calls), 6)
        self.assertTrue(any(line.startswith("two|validate") for line in calls))
        summary = self.summary.read_text(encoding="utf-8")
        self.assertIn("one` | failure", summary)
        self.assertIn("two` | success", summary)

    def test_terraform_reports_missing_roots_and_checks_existing_roots(self):
        """Report missing roots without skipping valid roots."""
        self._install_terraform_stub()
        (self.root / "valid").mkdir()
        result = self._run_script("terraform-validate.sh", TF_DIRECTORY="valid,missing")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(self.log.read_text(encoding="utf-8").splitlines()), 3)
        summary = self.summary.read_text(encoding="utf-8")
        self.assertIn("valid` | success", summary)
        self.assertIn("missing` | failure", summary)

    def _install_tflint_stub(self):
        """Stub TFLint and allow a selected root to fail linting."""
        self._executable(
            "tflint",
            "#!/usr/bin/env bash\n"
            'printf "%s|%s\\n" "${PWD##*/}" "$*" >>"$TOOL_LOG"\n'
            'if [[ "${FAIL_ROOT:-}" == "${PWD##*/}" && "${1:-}" != --init ]]; then\n'
            "  exit 9\n"
            "fi\n",
        )

    def test_tflint_init_runs_for_each_root(self):
        """Initialize TFLint plugins separately for each root."""
        self._install_tflint_stub()
        (self.root / "one").mkdir()
        (self.root / "two").mkdir()
        result = self._run_script("tflint.sh", "init", TF_DIRECTORY="one,two")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self.log.read_text(encoding="utf-8").splitlines(),
            ["one|--init", "two|--init"],
        )

    def test_tflint_lints_all_roots_and_preserves_failure(self):
        """Lint every root and fail if any root has findings."""
        self._install_tflint_stub()
        (self.root / "one").mkdir()
        (self.root / "two").mkdir()
        result = self._run_script(
            "tflint.sh", "lint", TF_DIRECTORY="one,two", FAIL_ROOT="one"
        )
        self.assertEqual(result.returncode, 1)
        calls = self.log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(calls, ["one|--format compact", "two|--format compact"])

    def test_tflint_rejects_invalid_operation(self):
        """Reject unsupported TFLint subcommands."""
        result = self._run_script("tflint.sh", "bad", TF_DIRECTORY=".")
        self.assertEqual(result.returncode, 2)

    def test_run_command_requires_and_propagates_command(self):
        """Require a command and propagate its process status."""
        result = self._run_script("run-command.sh", COMMAND="printf success")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "success")

        result = self._run_script("run-command.sh", COMMAND="")
        self.assertEqual(result.returncode, 1)
        result = self._run_script("run-command.sh", COMMAND="exit 7")
        self.assertEqual(result.returncode, 7)

    def _install_github_stubs(self):
        """Stub gh and jq to return a controlled alert count."""
        self._executable(
            "gh",
            "#!/usr/bin/env bash\n"
            'printf "%s\\n" "$*" >>"$GH_LOG"\n'
            'printf "%s\\n" "${MOCK_ALERTS_JSON:-[]}"\n',
        )
        self._executable(
            "jq",
            "#!/usr/bin/env bash\n"
            "cat >/dev/null\n"
            'printf "%s\\n" "${MOCK_ALERT_COUNT:-0}"\n',
        )

    def test_github_alerts_require_token_and_fail_on_open_alerts(self):
        """Require credentials and fail when alerts are found."""
        self._install_github_stubs()
        gh_log = self.root / "gh.log"
        result = self._run_script(
            "github-alerts.sh",
            "dependabot",
            GH_TOKEN="",
            REPOSITORY="owner/repo",
            GH_LOG=gh_log,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Pass github-security-token", result.stdout)

        result = self._run_script(
            "github-alerts.sh",
            "dependabot",
            GH_TOKEN="test-token",
            GH_HOST="https://github.com",
            REPOSITORY="owner/repo",
            GH_LOG=gh_log,
            MOCK_ALERT_COUNT="1",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Open high/critical Dependabot alerts", result.stdout)
        self.assertIn("owner/repo/dependabot/alerts", gh_log.read_text())

    def test_github_alerts_pass_when_no_alerts_are_open(self):
        """Pass when no secret-scanning alerts are open."""
        self._install_github_stubs()
        result = self._run_script(
            "github-alerts.sh",
            "secret-scanning",
            GH_TOKEN="test-token",
            GH_HOST="https://github.com",
            REPOSITORY="owner/repo",
            GH_LOG=self.root / "gh.log",
            MOCK_ALERT_COUNT="0",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Open secret-scanning alerts: 0", self.summary.read_text())

    def _prepare_release_fixture(self):
        """Create release notes and a mocked GitHub CLI."""
        notes = self.root / "docs" / "releases"
        notes.mkdir(parents=True)
        (notes / "v1.2.3.md").write_text("# v1.2.3\n", encoding="utf-8")
        self._executable(
            "gh",
            "#!/usr/bin/env bash\n"
            'printf "%s\\n" "$*" >>"$GH_LOG"\n'
            'if [[ "$1" == release && "$2" == view ]]; then\n'
            '  [[ "${RELEASE_EXISTS:-false}" == true ]]\n'
            "fi\n",
        )

    def test_release_script_rejects_invalid_tag_and_missing_notes(self):
        """Reject invalid tags and missing release notes."""
        self._prepare_release_fixture()
        result = self._run_script("create-release.sh", cwd=self.root, TAG="1.2.3")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Release tags must look like", result.stdout)

        result = self._run_script("create-release.sh", cwd=self.root, TAG="v2.0.0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Release notes missing", result.stdout)
        self.assertFalse(self.log.exists())

    def test_release_script_creates_and_updates_release(self):
        """Create a release or edit the existing release with notes."""
        self._prepare_release_fixture()
        values = {
            "GH_HOST": "https://github.com",
            "GH_LOG": self.log,
            "TAG": "v1.2.3",
        }
        result = self._run_script("create-release.sh", cwd=self.root, **values)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("release create v1.2.3 --verify-tag", self.log.read_text())

        self.log.unlink()
        result = self._run_script(
            "create-release.sh",
            cwd=self.root,
            RELEASE_EXISTS="true",
            **values,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("release edit v1.2.3 --title v1.2.3", self.log.read_text())


if __name__ == "__main__":
    unittest.main()
