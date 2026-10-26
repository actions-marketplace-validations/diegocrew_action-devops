#!/usr/bin/env bash
# Create or update the GitHub release for a version tag, using
# docs/releases/<tag>.md as the release notes.
# Env: GH_TOKEN, GH_HOST (server URL), GH_REPO, TAG.
set -euo pipefail

if [[ ! "${TAG:-}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "::error::Release tags must look like v1.2.3, got: ${TAG:-<empty>}"
  exit 1
fi
notes="docs/releases/$TAG.md"
if [[ ! -f "$notes" ]]; then
  echo "::error::Release notes missing: $notes"
  exit 1
fi
if ! grep -qF "]($TAG.md)" docs/releases/README.md; then
  echo "::error::Add $TAG to the table in docs/releases/README.md"
  exit 1
fi

export GH_HOST="${GH_HOST#*://}"
if gh release view "$TAG" >/dev/null 2>&1; then
  gh release edit "$TAG" --title "$TAG" --notes-file "$notes"
else
  gh release create "$TAG" --verify-tag --title "$TAG" --notes-file "$notes"
fi
