"""Exercise hosted-runner Bash and real virtualenv paths on every OS."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / ".github" / "scripts"
BASH: str | None
if os.name == "nt":
    BASH = str(Path(os.environ["ProgramFiles"]) / "Git" / "bin" / "bash.exe")
elif sys.platform == "darwin":
    BASH = "/bin/bash"
else:
    BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "requires Bash")
class PlatformTests(unittest.TestCase):
    """Run without POSIX-only executable stubs, including on Windows."""

    def run_bash(self, command, *args, **values):
        """Use Git Bash on Windows rather than a WSL launcher."""
        env = os.environ.copy()
        env["PATH"] = os.pathsep.join((str(Path(sys.executable).parent), env["PATH"]))
        env["PYTHON_EXECUTABLE"] = sys.executable
        env.update(values)
        return subprocess.run(
            [BASH, "-e", "-u", "-o", "pipefail", "-c", command, "test", *args],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_platform_guard_reports_each_unsupported_check(self):
        """Linux-only checks are errors on other runners, not silent skips."""
        for runner in ("Linux", "macOS", "Windows"):
            for check in ("LINT", "DOCKER", "TRIVY", "VERSIONS"):
                with self.subTest(runner=runner, check=check):
                    flags = dict.fromkeys(
                        ("LINT", "DOCKER", "TRIVY", "VERSIONS"), "false"
                    )
                    flags[check] = "true"
                    result = self.run_bash(
                        'bash "$1"',
                        str(SCRIPTS / "validate-platform.sh"),
                        RUNNER_OS=runner,
                        **flags,
                    )
                    self.assertEqual(result.returncode, 0 if runner == "Linux" else 1)
                    if runner != "Linux":
                        self.assertIn("::error::", result.stdout)
                        self.assertIn(check.lower(), result.stdout)

    def test_portable_only_configuration_is_accepted(self):
        """All supported OSes accept a configuration without Linux-only checks."""
        for runner in ("Linux", "macOS", "Windows"):
            result = self.run_bash(
                'bash "$1"',
                str(SCRIPTS / "validate-platform.sh"),
                RUNNER_OS=runner,
                LINT="false",
                DOCKER="false",
                TRIVY="false",
                VERSIONS="false",
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_virtualenv_with_spaces_and_native_runner_path(self):
        """Create and execute a real environment, including Windows Scripts."""
        runner = (
            "Windows"
            if os.name == "nt"
            else "macOS"
            if sys.platform == "darwin"
            else "Linux"
        )
        with tempfile.TemporaryDirectory(prefix="runner space ") as directory:
            result = self.run_bash(
                'source "$1"; create_python_env "$RUNNER_TEMP/venv space"; '
                "\"$VENV_PYTHON\" -c 'import sys; print(sys.prefix)'",
                str(SCRIPTS / "runtime.sh"),
                RUNNER_OS=runner,
                RUNNER_TEMP=directory,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                Path(result.stdout.strip()).resolve(),
                (Path(directory) / "venv space").resolve(),
            )


if __name__ == "__main__":
    unittest.main()
