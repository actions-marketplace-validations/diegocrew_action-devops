#!/usr/bin/env bash
# Run a trusted build/test shell command supplied by the calling workflow.
# Env: COMMAND.
set -euo pipefail

if [[ -z "${COMMAND:-}" ]]; then
  echo "::error::A test command is required"
  exit 1
fi
bash -e -o pipefail -c "$COMMAND"