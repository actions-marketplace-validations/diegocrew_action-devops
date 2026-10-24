#!/usr/bin/env bash
# Install optional requirements and run the trusted test command.
# Env: REQUIREMENTS (optional), TEST_COMMAND.
set -euo pipefail

if [[ -n "${REQUIREMENTS:-}" ]]; then
  python -m pip install -r "$REQUIREMENTS"
fi
bash -e -o pipefail -c "$TEST_COMMAND"
