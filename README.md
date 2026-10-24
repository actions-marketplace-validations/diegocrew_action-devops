# action-devops

Reusable, parallel DevOps and security checks, configured through
`.github/workflows/allinone.yml`. Call it at **job level**, not as a step: a
composite action cannot create parallel jobs.

## Use from any repository

```yaml
name: DevOps checks
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  checks:
    uses: diegocrew/action-devops/.github/workflows/allinone.yml@main
    with:
      mode: audit
      python: true
      python-requirements: requirements-dev.txt
      python-command: python -m pytest
      docker: true
      terraform: true
      terraform-directory: infrastructure
```

Replace `main` with a reviewed full commit SHA for production use. The workflow
checks out the **calling repository** at the event revision (including the PR
merge revision), not this repository. It runs on GitHub-hosted Ubuntu runners.

## Checks

All enabled checks run independently in parallel after configuration validation.

| Input | Default | Check |
| --- | --- | --- |
| `trivy` | `true` | Filesystem vulnerabilities, secrets, and IaC misconfiguration |
| `versions` | `true` | Renovate dependency lookups, including GitHub Actions, Terraform providers/modules, Docker images, and supported language dependencies |
| `lint` | `true` | Super-Linter's supported languages and configuration files |
| `python` | `false` | Python setup, optional requirements installation, and test command |
| `docker` | `false` | Docker build; never pushes an image |
| `terraform` | `false` | Recursive format check, backend-free init, and root-module validation; never plans or applies |

Set any check to `false` to skip it. Enable project-specific checks only when their
files exist; missing explicitly requested files are errors, not silent skips.
Configure Super-Linter using its standard repository configuration files.
Version checks use Renovate's supported managers and respect repository Renovate
configuration; ignored, disabled, unsupported, or unresolvable dependencies cannot
be guaranteed current. Available updates and lookup errors fail the version check.
No infrastructure credentials are supplied.

| Additional input | Default | Purpose |
| --- | --- | --- |
| `mode` | `audit` | Failure/remediation policy below |
| `severity` | `HIGH,CRITICAL` | Trivy severity threshold |
| `python-version` | `3.12` | Python interpreter version |
| `python-requirements` | empty | Requirements file to install; empty skips installation |
| `python-command` | `python -m unittest discover -v` | Test shell command; install pytest in your requirements if using the example |
| `docker-context` | `.` | Docker build context |
| `dockerfile` | `Dockerfile` | Dockerfile path relative to repository root |
| `terraform-directory` | `.` | Root module directory; call separately for independent roots |
| `terraform-version` | `latest` | Terraform CLI version; pin for reproducible runs |

## Modes

- **audit**: report findings and tolerate failed check jobs so the workflow can
  continue. Individual jobs may still show failures.
- **restrict**: check failures fail the workflow and dependent caller jobs.
  Other parallel checks finish to provide a complete report; this does not cancel
  unrelated jobs in the caller.
- **advanced**: audit behavior plus an attempt to open dependency update/fix PRs
  with Renovate. It does not auto-merge or attempt arbitrary source-code repairs.
  Fix attempts run only on `push`, `schedule`, or `workflow_dispatch` on the
  repository's default branch, never on pull request events. `versions: false`
  also disables fix attempts.

Invalid modes always fail. The final `summary` job reports passed, failed, and
skipped jobs; tool details remain in individual logs and dependency summaries.
Use the summary check for branch protection when using restrict mode.

### Advanced-mode credentials

Pass a dedicated bot token explicitly; normal checks need only `contents: read`
and do not need this secret:

```yaml
jobs:
  checks:
    uses: diegocrew/action-devops/.github/workflows/allinone.yml@main
    with:
      mode: advanced
    secrets:
      renovate-token: ${{ secrets.RENOVATE_TOKEN }}
```

Use a GitHub App installation token or fine-grained PAT restricted to the calling
repository, with contents and pull requests write access, issues write access
if using Renovate's dependency dashboard, and workflows write access for Actions
updates. Organization policies must allow bot PR creation. Missing credentials
or failed PR attempts are reported but remain non-blocking. Review generated PRs;
not every finding has an automated fix. Existing Renovate schedules, package
rules, and PR limits may defer updates.

## Security boundaries

Use `pull_request`, not `pull_request_target`, to test untrusted changes. Python
tests, package installation, Dockerfiles, Terraform providers, and repository
linter configuration can execute repository-controlled code: do not pass secrets
or grant write permissions to these jobs. `python-command` is intentionally a
shell command and must come from trusted workflow configuration, never event
titles, branch names, or other untrusted input.

Checkouts do not persist credentials. The separate advanced-mode bot job does
not check out or execute test code and disables Renovate package scripts and
post-upgrade commands. The caller must still trust the default branch and its
Renovate configuration. Third-party actions are pinned to commit SHAs; Renovate
can propose updates to those pins.