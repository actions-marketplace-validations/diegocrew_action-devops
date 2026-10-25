#!/usr/bin/env bash
# Lint CloudFormation templates with a pinned cfn-lint. Env: CFN_DIRECTORY.
set -euo pipefail

if [[ ! -d "$CFN_DIRECTORY" ]]; then
  echo "::error::CloudFormation directory does not exist: $CFN_DIRECTORY"
  exit 1
fi
mapfile -d '' templates < <(find "$CFN_DIRECTORY" -type f \( -iname '*.yaml' -o -iname '*.yml' -o -iname '*.json' -o -iname '*.template' \) -print0)
if ((${#templates[@]} == 0)); then
  echo "::error::No YAML, JSON, or .template CloudFormation templates found in $CFN_DIRECTORY"
  exit 1
fi
python3 -m venv "$RUNNER_TEMP/cfn-lint"
"$RUNNER_TEMP/cfn-lint/bin/python" -m pip install --disable-pip-version-check cfn-lint==1.58.0
"$RUNNER_TEMP/cfn-lint/bin/cfn-lint" "${templates[@]}"
