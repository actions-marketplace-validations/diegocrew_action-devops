#!/usr/bin/env bash
# Lint CloudFormation templates with a pinned cfn-lint. Env: CFN_DIRECTORY.
set -euo pipefail

# shellcheck source=SCRIPTDIR/runtime.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/runtime.sh"
if [[ ! -d "$CFN_DIRECTORY" ]]; then
  echo "::error::CloudFormation directory does not exist: $CFN_DIRECTORY"
  exit 1
fi
templates=()
while IFS= read -r -d '' template; do
  templates+=("$template")
done < <(find "$CFN_DIRECTORY" -type f \( -iname '*.yaml' -o -iname '*.yml' -o -iname '*.json' -o -iname '*.template' \) -print0)
if [[ -z "${templates[*]-}" ]]; then
  echo "::error::No YAML, JSON, or .template CloudFormation templates found in $CFN_DIRECTORY"
  exit 1
fi
create_python_env "$RUNNER_TEMP/cfn-lint"
"$VENV_PYTHON" -m pip install --disable-pip-version-check cfn-lint==1.58.0
"$VENV_BIN/cfn-lint" "${templates[@]}"
