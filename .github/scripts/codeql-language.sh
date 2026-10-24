#!/usr/bin/env bash
# Validate the CodeQL language. Env: CODEQL_LANGUAGE.
set -euo pipefail

case "${CODEQL_LANGUAGE:-}" in
  javascript-typescript|python|ruby|c-cpp|go|java-kotlin|csharp) ;;
  *) echo "::error::codeql-language must be one supported language; see README"; exit 1 ;;
esac
