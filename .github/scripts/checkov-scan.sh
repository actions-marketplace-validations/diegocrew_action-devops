#!/usr/bin/env bash
# Run pinned Checkov security and best-practice checks on IaC in the workspace.
set -euo pipefail

python3 -m venv "$RUNNER_TEMP/checkov"
"$RUNNER_TEMP/checkov/bin/python" -m pip install --disable-pip-version-check checkov==3.3.30

args=(--directory . --framework "terraform,cloudformation,arm,bicep,github_actions" --compact)
# Same config file Super-Linter reads, so existing skips keep working.
if [[ -f .github/linters/.checkov.yaml ]]; then
  args+=(--config-file .github/linters/.checkov.yaml)
fi
status=0
"$RUNNER_TEMP/checkov/bin/checkov" "${args[@]}" | tee "$RUNNER_TEMP/checkov.log" || status=$?

if ! grep -q "Passed checks:" "$RUNNER_TEMP/checkov.log"; then
  echo "::notice::Checkov found no Terraform, CloudFormation, ARM, Bicep, or workflow files to scan"
  echo "Checkov: no Terraform, CloudFormation, ARM, Bicep, or workflow files found." >>"$GITHUB_STEP_SUMMARY"
fi
exit "$status"
