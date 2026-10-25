#!/usr/bin/env bash
# Compile every Bicep template and parameter file without deploying.
# Env: BICEP_DIRECTORY.
set -euo pipefail

if [[ ! -d "$BICEP_DIRECTORY" ]]; then
  echo "::error::Bicep directory does not exist: $BICEP_DIRECTORY"
  exit 1
fi
mapfile -d '' templates < <(find "$BICEP_DIRECTORY" -type f -name '*.bicep' -print0)
mapfile -d '' parameters < <(find "$BICEP_DIRECTORY" -type f -name '*.bicepparam' -print0)
if ((${#templates[@]} == 0 && ${#parameters[@]} == 0)); then
  echo "::error::No .bicep or .bicepparam files found in $BICEP_DIRECTORY"
  exit 1
fi
az bicep install
for template in "${templates[@]}"; do
  echo "::group::Compile $template"
  az bicep build --file "$template" --outfile "$RUNNER_TEMP/template.json"
  echo "::endgroup::"
done
for parameter_file in "${parameters[@]}"; do
  echo "::group::Compile $parameter_file"
  az bicep build-params --file "$parameter_file" --outfile "$RUNNER_TEMP/parameters.json"
  echo "::endgroup::"
done
