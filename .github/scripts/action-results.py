"""Convert composite-action step outcomes into summarize.py results.

Env: STEPS (toJSON(steps) from action.yml). Prints the RESULTS JSON.
"""

# pylint: disable=invalid-name  # Hyphenated like the other check scripts.

import json
import os

# Group -> check -> step ids whose outcomes make up that check.
CHECKS = {
    "quality": {"lint": ["lint"]},
    "build-test": {
        "python": ["python-setup", "python"],
        "docker": ["docker"],
        "node": ["node-setup", "node"],
        "go": ["go-setup", "go"],
        "dotnet": ["dotnet-setup", "dotnet"],
    },
    "iac": {
        "terraform": ["terraform-setup", "terraform"],
        "tflint": ["tflint-setup", "tflint-init", "tflint"],
        "bicep": ["bicep"],
        "cloudformation": ["cloudformation"],
    },
    "security": {
        "trivy": ["trivy"],
        "iac-security": ["iac-security"],
        "codeql": [
            "codeql-languages",
            "codeql-mode",
            "codeql-init",
            "codeql-autobuild",
            "codeql-analyze",
        ],
        "dependabot": ["dependabot"],
        "dependency-review": ["dependency-review"],
        "secret-scanning": ["secret-scanning"],
    },
    "dependencies": {
        "versions": ["versions-lookup", "versions"],
        "fixes": ["fixes-credentials", "fixes"],
    },
}


def outcome(step_ids, steps):
    """Return the combined outcome of a check, or "" if none of it ran."""
    outcomes = [steps.get(step_id, {}).get("outcome", "") for step_id in step_ids]
    for status in ("failure", "cancelled"):
        if status in outcomes:
            return status
    return "success" if "success" in outcomes else ""


steps_context = json.loads(os.environ["STEPS"])
results: dict[str, dict] = {"configuration": {"result": "success"}}
for group, checks in CHECKS.items():
    results[group] = {
        "result": "success",
        "outputs": {
            check: outcome(ids, steps_context) for check, ids in checks.items()
        },
    }
print(json.dumps(results))
