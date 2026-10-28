#!/usr/bin/env bash
# Validate one or more CodeQL languages and emit them as a JSON matrix.
# Env: CODEQL_LANGUAGE (comma- or newline-separated). Writes `languages` and
# `build-mode` (none, autobuild, or mixed) to $GITHUB_OUTPUT.
set -euo pipefail

# shellcheck source=SCRIPTDIR/list.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/list.sh"
languages=()
compiled=false
interpreted=false
while IFS= read -r language; do
  case "$language" in
    javascript-typescript | python | ruby) interpreted=true ;;
    c-cpp | go | java-kotlin | csharp) compiled=true ;;
    *)
      echo "::error::Unsupported codeql-language: $language; see README"
      exit 1
      ;;
  esac
  [[ " ${languages[*]-} " == *" $language "* ]] || languages+=("$language")
done < <(split_list "${CODEQL_LANGUAGE:-}")

if [[ -z "${languages[*]-}" ]]; then
  echo "::error::codeql-language must name at least one supported language; see README"
  exit 1
fi
# Values are validated above, so they are safe to embed in JSON.
json=$(printf '"%s",' "${languages[@]}")
echo "languages=[${json%,}]" >>"$GITHUB_OUTPUT"
if [[ "$compiled" == true && "$interpreted" == true ]]; then
  build_mode=mixed
elif [[ "$compiled" == true ]]; then
  build_mode=autobuild
else
  build_mode=none
fi
echo "build-mode=$build_mode" >>"$GITHUB_OUTPUT"
echo "CodeQL languages: ${languages[*]}"
