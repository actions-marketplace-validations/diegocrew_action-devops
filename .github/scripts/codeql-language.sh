#!/usr/bin/env bash
# Validate one or more CodeQL languages and emit them as a JSON matrix.
# Env: CODEQL_LANGUAGE (comma- or newline-separated). Writes `languages` to
# $GITHUB_OUTPUT.
set -euo pipefail

# shellcheck source=SCRIPTDIR/list.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/list.sh"
languages=()
while IFS= read -r language; do
  case "$language" in
    javascript-typescript | python | ruby | c-cpp | go | java-kotlin | csharp) ;;
    *)
      echo "::error::Unsupported codeql-language: $language; see README"
      exit 1
      ;;
  esac
  [[ " ${languages[*]} " == *" $language "* ]] || languages+=("$language")
done < <(split_list "${CODEQL_LANGUAGE:-}")

if ((${#languages[@]} == 0)); then
  echo "::error::codeql-language must name at least one supported language; see README"
  exit 1
fi
# Values are validated above, so they are safe to embed in JSON.
json=$(printf '"%s",' "${languages[@]}")
echo "languages=[${json%,}]" >>"$GITHUB_OUTPUT"
echo "CodeQL languages: ${languages[*]}"
