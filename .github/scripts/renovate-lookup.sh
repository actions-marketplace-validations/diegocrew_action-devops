#!/usr/bin/env bash
# Look up dependency updates at the checked-out revision with Renovate, no PRs.
# Writes a JSON log to $RUNNER_TEMP/action-devops-renovate.json.
# Env: GITHUB_COM_TOKEN.
set -euo pipefail

printf '{}\n' >"$RUNNER_TEMP/action-devops-renovate-config.json"
docker run --rm --user "$(id -u):$(id -g)" \
  --volume "$GITHUB_WORKSPACE:/workspace" \
  --volume "$RUNNER_TEMP:/tmp" --workdir /workspace \
  --env GITHUB_COM_TOKEN \
  --env LOG_FILE=/tmp/action-devops-renovate.json \
  --env LOG_FILE_LEVEL=debug \
  --env RENOVATE_CONFIG_FILE=/tmp/action-devops-renovate-config.json \
  --env RENOVATE_ONBOARDING=false \
  --env RENOVATE_ALLOW_SCRIPTS=false \
  --env RENOVATE_IGNORE_SCRIPTS=true \
  --env 'RENOVATE_ALLOWED_COMMANDS=[]' \
  ghcr.io/renovatebot/renovate:44.182.0 \
  --platform=local --dry-run=lookup
