# Unreleased

## Added

- Ubuntu, macOS, and Windows runner selection for portable checks through the
  reusable workflow's `runner` input, defaulting to `ubuntu-latest`.
- Three-OS CI matrices for reusable workflows and the composite action, real IaC
  tool fixtures, native virtualenv tests, and mode/platform failure assertions.

## Changed

- Linux-only integrations (Super-Linter, Docker, Trivy, and Renovate) remain on
  Ubuntu in reusable workflows. The composite action explicitly rejects them on
  macOS/Windows, even in audit mode; disable these checks or use reusable workflows.
- IaC scripts support macOS system Bash and Windows virtualenv layouts. Python is
  provisioned explicitly for reporting, CloudFormation, and Checkov.
- Bicep uses the standalone CLI pinned to v0.48.1 rather than requiring Azure CLI.
- Shell scripts are checked out with LF endings on every OS.

## Fixed

- CI lint regressions: shared Terraform root parsing avoids duplicate code,
  Bash discovery is typed for missing executables, README tables are formatted,
  and workspace-action lint exceptions no longer depend on changing line numbers.
