#!/usr/bin/env bash
# Fail when the repository has open GitHub security alerts.
# Usage: github-alerts.sh dependabot|secret-scanning
# Env: GH_TOKEN, GH_HOST (server URL), REPOSITORY.
set -euo pipefail

case "${1:-}" in
  dependabot)
    label="high/critical Dependabot"
    permission="Dependabot alerts"
    endpoint="repos/$REPOSITORY/dependabot/alerts?state=open&severity=high,critical&per_page=100"
    ;;
  secret-scanning)
    label="secret-scanning"
    permission="Secret scanning alerts"
    endpoint="repos/$REPOSITORY/secret-scanning/alerts?state=open&per_page=100"
    ;;
  *)
    echo "::error::Usage: github-alerts.sh dependabot|secret-scanning"
    exit 2
    ;;
esac

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "::error::Pass github-security-token with $permission read permission"
  exit 1
fi
export GH_HOST="${GH_HOST#*://}"
# gh rejects --slurp combined with --jq, so count with jq.
count=$(gh api --paginate --slurp "$endpoint" | jq '[.[][]] | length')
echo "Open $label alerts: $count" >>"$GITHUB_STEP_SUMMARY"
if ((count > 0)); then
  echo "::error::Open $label alerts require attention"
  exit 1
fi
