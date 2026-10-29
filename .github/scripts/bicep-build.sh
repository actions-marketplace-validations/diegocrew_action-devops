#!/usr/bin/env bash
# Compile every Bicep template and parameter file without deploying.
# Env: BICEP_DIRECTORY.
set -euo pipefail

# shellcheck source=SCRIPTDIR/runtime.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/runtime.sh"
if [[ ! -d "$BICEP_DIRECTORY" ]]; then
  echo "::error::Bicep directory does not exist: $BICEP_DIRECTORY"
  exit 1
fi
templates=()
parameters=()
while IFS= read -r -d '' template; do
  templates+=("$template")
done < <(find "$BICEP_DIRECTORY" -type f -name '*.bicep' -print0)
while IFS= read -r -d '' parameter_file; do
  parameters+=("$parameter_file")
done < <(find "$BICEP_DIRECTORY" -type f -name '*.bicepparam' -print0)
if [[ -z "${templates[*]-}${parameters[*]-}" ]]; then
  echo "::error::No .bicep or .bicepparam files found in $BICEP_DIRECTORY"
  exit 1
fi
case "${RUNNER_OS:-}:$RUNNER_ARCH" in
  Linux:X64) asset="bicep-linux-x64" ;;
  Linux:ARM64) asset="bicep-linux-arm64" ;;
  macOS:X64) asset="bicep-osx-x64" ;;
  macOS:ARM64) asset="bicep-osx-arm64" ;;
  Windows:X64) asset="bicep-win-x64.exe" ;;
  Windows:ARM64) asset="bicep-win-arm64.exe" ;;
  *)
    echo "::error::Unsupported Bicep platform: ${RUNNER_OS:-}:$RUNNER_ARCH"
    exit 1
    ;;
esac
bicep="$RUNNER_TEMP/$asset"
curl --fail --silent --show-error --location --retry 3 \
  "https://github.com/Azure/bicep/releases/download/v0.48.1/$asset" --output "$bicep"
chmod +x "$bicep"
for template in ${templates[@]+"${templates[@]}"}; do
  echo "::group::Compile $template"
  "$bicep" build "$template" --outfile "$RUNNER_TEMP/template.json"
  echo "::endgroup::"
done
for parameter_file in ${parameters[@]+"${parameters[@]}"}; do
  echo "::group::Compile $parameter_file"
  "$bicep" build-params "$parameter_file" --outfile "$RUNNER_TEMP/parameters.json"
  echo "::endgroup::"
done
