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
    parts = re.split(r"^  ([a-z][a-z0-9-]*):\s*$", section, flags=re.MULTILINE)
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


if __name__ == "__main__":
    unittest.main()
