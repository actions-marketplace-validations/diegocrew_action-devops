"""Report outdated dependencies from a Renovate lookup log. Env: REPORT."""

# pylint: disable=invalid-name  # Hyphenated like the other check scripts.

import json
import os
import sys

found = False
updates = []
errors = []
if not os.path.isfile(os.environ["REPORT"]):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write(
            "## Dependency versions\n\n"
            "The Renovate lookup failed before writing a report; "
            "see the lookup step log.\n"
        )
    print("::error::Renovate lookup produced no report; see the lookup step log")
    sys.exit(1)
with open(os.environ["REPORT"], encoding="utf-8") as report:
    for line in report:
        record = json.loads(line)
        if record.get("level", 0) >= 50:
            errors.append(record.get("msg", "Renovate error"))
        if record.get("msg") != "packageFiles with updates":
            continue
        found = True
        for manager, files in record["config"].items():
            for package in files:
                for dep in package.get("deps", []):
                    if dep.get("warnings") or dep.get("skipReason") == "lookup-failed":
                        errors.append(f"Lookup failed: {dep.get('depName', manager)}")
                    for update in dep.get("updates", []):
                        updates.append(
                            f"{package['packageFile']}: {dep.get('depName', manager)} "
                            f"{dep.get('currentValue', '?')} -> "
                            f"{update.get('newValue', update.get('newVersion', '?'))}"
                        )
if not found:
    errors.append("Renovate did not produce a dependency lookup report")
# Keep dependency metadata out of Markdown/HTML markup.
messages = [
    message.replace("\n", " ").replace("\r", " ") for message in updates + errors
]
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    summary.write("## Dependency versions\n\n")
    summary.writelines(f"    {message}\n" for message in messages)
    if not messages:
        summary.write("No supported dependency updates found.\n")
for message in messages:
    print(message)
print(f"{len(updates)} available updates; {len(errors)} lookup errors")
sys.exit(1 if messages else 0)
