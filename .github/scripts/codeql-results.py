"""Fail unless every requested CodeQL language analyzed successfully.

Env: LANGUAGES (JSON list from codeql-language.sh; empty if validation failed),
RESULTS (toJSON of the analysis matrix outputs: language -> job.status).
"""

# pylint: disable=invalid-name  # Hyphenated like the other check scripts.

import json
import os
import sys

languages = json.loads(os.environ.get("LANGUAGES") or "[]")
results = json.loads(os.environ.get("RESULTS") or "{}") or {}
failed = not languages
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    summary.write("## CodeQL\n\n| Language | Result |\n| --- | --- |\n")
    if not languages:
        summary.write("| (configuration) | failure |\n")
    for language in languages:
        # A leg that never reported (for example, cancelled early) counts as failed.
        result = results.get(language) or "missing"
        summary.write(f"| {language} | {result} |\n")
        failed = failed or result != "success"
if failed:
    print("::error::One or more CodeQL analyses did not succeed; see the summary")
sys.exit(1 if failed else 0)
