"""Summarize group results and enforce the mode policy.

Env: RESULTS (toJSON(needs) from allinone.yml), MODE.
"""
import json
import os
import sys

results = json.loads(os.environ["RESULTS"])
failures = []
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    summary.write("## All-in-one results\n\n| Group | Check | Result |\n| --- | --- | --- |\n")
    for group, job in results.items():
        if group == "configuration":
            continue
        # Each group reports its checks' job.status; disabled checks are empty.
        checks = {name: value or "skipped" for name, value in (job.get("outputs") or {}).items()}
        if job["result"] in ("failure", "cancelled") and not any(
            value not in ("success", "skipped") for value in checks.values()
        ):
            checks["(workflow)"] = job["result"]
        if not checks:
            checks["(all)"] = job["result"]
        for name, result in checks.items():
            summary.write(f"| {group} | {name} | {result} |\n")
            if result not in ("success", "skipped"):
                failures.append(f"{group}/{name}")
    summary.write("\nDetailed findings are in each job's logs and summaries.\n")
invalid = results["configuration"]["result"] != "success"
if failures:
    print("Failed checks: " + ", ".join(failures))
sys.exit(1 if invalid or (os.environ["MODE"] == "restrict" and failures) else 0)
