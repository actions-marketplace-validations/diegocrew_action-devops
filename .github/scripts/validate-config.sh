#!/usr/bin/env bash
# Validate shared configuration. Env: MODE.
set -euo pipefail

case "${MODE:-}" in
  audit | restrict | advanced) ;;
  *)
    echo "::error::mode must be audit, restrict, or advanced"
    exit 1
    ;;
esac
