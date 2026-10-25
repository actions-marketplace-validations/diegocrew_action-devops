#!/usr/bin/env bash
# Format-check and validate Terraform root modules without a backend.
# Env: TF_DIRECTORY (one or more roots, comma- or newline-separated).
# Every root is checked; the script fails at the end if any root failed.
set -uo pipefail

export TF_IN_AUTOMATION=true TF_INPUT=false
# shellcheck source=SCRIPTDIR/list.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/list.sh"
mapfile -t roots < <(split_list "${TF_DIRECTORY:-}")
if (( ${#roots[@]} == 0 )); then
  echo "::error::terraform-directory must name at least one root module"
  exit 1
fi

failed=()
for root in "${roots[@]}"; do
  echo "::group::Terraform $root"
  if [[ ! -d "$root" ]]; then
    echo "::error::Terraform directory does not exist: $root"
    result=1
  else
    (
      set -e
      cd -- "$root"
      terraform fmt -check -recursive
      terraform init -backend=false -input=false
      terraform validate -no-color
    )
    result=$?
  fi
  echo "::endgroup::"
  if (( result == 0 )); then
    echo "| \`$root\` | success |" >> "$RUNNER_TEMP/terraform-results.md"
  else
    echo "::error::Terraform checks failed in $root"
    echo "| \`$root\` | failure |" >> "$RUNNER_TEMP/terraform-results.md"
    failed+=("$root")
  fi
done
{
  printf '## Terraform\n\n| Root | Result |\n| --- | --- |\n'
  cat "$RUNNER_TEMP/terraform-results.md"
} >> "$GITHUB_STEP_SUMMARY"
(( ${#failed[@]} == 0 ))