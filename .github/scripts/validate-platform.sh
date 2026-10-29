#!/usr/bin/env bash
# Linux-only checks must not be silently skipped by the composite action.
set -euo pipefail

if [[ "$RUNNER_OS" == Linux ]]; then
  exit 0
fi
unsupported=()
[[ "$LINT" == true ]] && unsupported+=(lint)
[[ "$DOCKER" == true ]] && unsupported+=(docker)
[[ "$TRIVY" == true ]] && unsupported+=(trivy)
[[ "$VERSIONS" == true ]] && unsupported+=(versions)
if [[ -n "${unsupported[*]-}" ]]; then
  echo "::error::Checks ${unsupported[*]} require Linux. Disable them on $RUNNER_OS or use the reusable workflow, which keeps Linux-only jobs on Ubuntu."
  exit 1
fi
