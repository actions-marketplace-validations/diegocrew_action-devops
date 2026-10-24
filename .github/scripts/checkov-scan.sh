#!/usr/bin/env bash
# Run pinned Checkov security and best-practice checks on IaC in the workspace.
set -euo pipefail

python3 -m venv "$RUNNER_TEMP/checkov"
"$RUNNER_TEMP/checkov/bin/python" -m pip install --disable-pip-version-check checkov==3.3.30
"$RUNNER_TEMP/checkov/bin/checkov" \
  --directory . \
  --framework terraform,cloudformation,arm,bicep \
  --compact
