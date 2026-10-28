#!/usr/bin/env bash
# Run TFLint in Terraform root modules.
# Usage: tflint.sh init|lint
# Env: TF_DIRECTORY (one or more roots, comma- or newline-separated).
# `init` installs plugins declared in each root's .tflint.hcl; `lint` runs
# them. Run them as separate steps so plugin code never sees the token used
# to download plugins. Every root is linted; failures are reported at the end.
set -uo pipefail

# shellcheck source=SCRIPTDIR/list.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/list.sh"
case "${1:-}" in
  init | lint) ;;
  *)
    echo "::error::Usage: tflint.sh init|lint"
    exit 2
    ;;
esac
roots=()
while IFS= read -r root; do
  roots+=("$root")
done < <(split_list "${TF_DIRECTORY:-}")
if [[ -z "${roots[*]-}" ]]; then
  echo "::error::terraform-directory must name at least one root module"
  exit 1
fi

failed=()
for root in "${roots[@]}"; do
  if [[ ! -d "$root" ]]; then
    echo "::error::Terraform directory does not exist: $root"
    failed+=("$root")
    continue
  fi
  echo "::group::TFLint $1 $root"
  if [[ "$1" == init ]]; then
    (cd -- "$root" && tflint --init)
  else
    (cd -- "$root" && tflint --format compact)
  fi
  result=$?
  echo "::endgroup::"
  if ((result != 0)); then
    echo "::error::TFLint $1 failed in $root"
    failed+=("$root")
  fi
done
[[ -z "${failed[*]-}" ]]
