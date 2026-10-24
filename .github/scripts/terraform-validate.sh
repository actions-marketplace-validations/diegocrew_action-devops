#!/usr/bin/env bash
# Format-check and validate a Terraform root module without a backend.
# Env: TF_DIRECTORY.
set -euo pipefail

export TF_IN_AUTOMATION=true TF_INPUT=false
cd -- "$TF_DIRECTORY"
terraform fmt -check -recursive
terraform init -backend=false -input=false
terraform validate -no-color
