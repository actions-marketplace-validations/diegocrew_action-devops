#!/usr/bin/env bash
# Build a Docker image without pushing it. Env: CONTEXT, DOCKERFILE.
set -euo pipefail

docker build --file "$DOCKERFILE" --tag action-devops-check:local -- "$CONTEXT"
