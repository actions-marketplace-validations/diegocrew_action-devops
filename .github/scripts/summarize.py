"""Summarize group results and enforce the mode policy.

Env: RESULTS (toJSON(needs) from allinone.yml), MODE.
"""

import json
import os
import sys

POLICY = {
    "audit": "failed checks are reported but do not fail this workflow.",
    "restrict": "any failed check fails this workflow.",
    "advanced": (
        "failed checks are reported but do not fail this workflow; "
        "dependency fix PRs may be attempted."
    ),
}
LABELS = {"success": "success", "skipped": "skipped", "cancelled": "**cancelled**"}


def label(status, active_mode):
    """Return a readable result label that keeps the raw result visible."""
    if status in LABELS:
        return LABELS[status]
    # A tolerated failure is still a failure.
    if active_mode in ("audit", "advanced"):
        return f"**{status}** (tolerated in {active_mode} mode)"
    return f"**{status}**"


results = json.loads(os.environ["RESULTS"])
mode = os.environ.get("MODE", "")
invalid = results["configuration"]["result"] != "success"
failures = []
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    summary.write("## All-in-one results\n\n")
    if invalid:
        summary.write(
            "**Invalid configuration**: see the `configuration` job. "
            "Checks did not run.\n\n"
        )
    else:
        summary.write(f"Mode: **{mode}**: {POLICY[mode]}\n\n")
    summary.write("| Group | Check | Result |\n| --- | --- | --- |\n")
    for group, job in results.items():
        if group == "configuration":
            continue
        # Each group reports its checks' job.status; disabled checks are empty.
        outputs = job.get("outputs") or {}
        checks = {name: value or "skipped" for name, value in outputs.items()}
        if job["result"] in ("failure", "cancelled") and not any(
            value not in ("success", "skipped") for value in checks.values()
        ):
            checks["(workflow)"] = job["result"]
        if not checks:
            checks["(all)"] = job["result"]
        for name, result in checks.items():
            summary.write(f"| {group} | {name} | {label(result, mode)} |\n")
            if result not in ("success", "skipped"):
                failures.append(f"{group}/{name}")
    if failures:
        summary.write(f"\n**{len(failures)} failed:** " + ", ".join(failures) + "\n")
    summary.write("\nDetailed findings are in each job's logs and summaries.\n")
if failures:
    print("Failed checks: " + ", ".join(failures))
sys.exit(1 if invalid or (mode == "restrict" and failures) else 0)
