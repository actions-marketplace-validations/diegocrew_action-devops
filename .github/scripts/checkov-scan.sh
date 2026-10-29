#!/usr/bin/env bash
# Run pinned Checkov security and best-practice checks on IaC in the workspace.
set -euo pipefail

# shellcheck source=SCRIPTDIR/runtime.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/runtime.sh"
create_python_env "$RUNNER_TEMP/checkov"
"$VENV_PYTHON" -m pip install --disable-pip-version-check checkov==3.3.30

args=(--directory . --framework "terraform,cloudformation,arm,bicep,github_actions" --compact)
# Same config file Super-Linter reads, so existing skips keep working.
if [[ -f .github/linters/.checkov.yaml ]]; then
  args+=(--config-file .github/linters/.checkov.yaml)
fi
status=0
# Checkov ships a Python script, whose shebang breaks on virtualenv paths with spaces.
"$VENV_PYTHON" "$VENV_BIN/checkov" "${args[@]}" | tee "$RUNNER_TEMP/checkov.log" || status=$?

if ((status == 0)) && ! grep -q "Passed checks:" "$RUNNER_TEMP/checkov.log"; then
  echo "::notice::Checkov found no Terraform, CloudFormation, ARM, Bicep, or workflow files to scan"
  echo "Checkov: no Terraform, CloudFormation, ARM, Bicep, or workflow files found." >>"$GITHUB_STEP_SUMMARY"
fi
exit "$status"
