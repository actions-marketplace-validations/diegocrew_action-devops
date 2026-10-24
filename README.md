# action-devops

Reusable, parallel DevOps and security checks, in three layers:

1. `.github/workflows/allinone.yml` is only configuration: it switches checks
   on or off and calls one reusable workflow per group.
2. Each group workflow in `.github/workflows/` runs its checks as parallel jobs.
3. Check logic lives in `.github/scripts/`, one script per check. Workflows
   only set up tools, pass inputs as environment variables, and call scripts
   or pinned actions.

Updating a check means editing its script or its group file, never the
orchestrator.
Call it at **job level**, not as a step: a composite action cannot create
parallel jobs.

| Workflow | Checks |
| --- | --- |
| `allinone.yml` | Validates `mode`, calls the groups below in parallel, and summarizes |
| `quality.yml` | `lint` |
| `build-test.yml` | `python`, `docker` |
| `iac.yml` | `terraform`, `bicep`, `cloudformation` |
| `security.yml` | `trivy`, `iac-security`, `codeql`, `dependabot`, `dependency-review`, `secret-scanning` |
| `dependencies.yml` | `versions`, plus advanced-mode fix PRs |

A group with every check off is skipped. `allinone.yml` calls the groups with
`$/.github/workflows/...`, which resolves to this repository at the same commit,
so pinning `allinone.yml` to a SHA pins every group too. Each group can also be
called directly with the same inputs.

| Script | Used by |
| --- | --- |
| `validate-config.sh` | `allinone.yml` configuration |
| `summarize.py` | `allinone.yml` summary |
| `python-tests.sh`, `docker-build.sh` | `build-test.yml` |
| `terraform-validate.sh`, `bicep-build.sh`, `cloudformation-lint.sh` | `iac.yml` |
| `checkov-scan.sh`, `codeql-language.sh`, `github-alerts.sh` | `security.yml` |
| `renovate-lookup.sh`, `renovate-report.py` | `dependencies.yml` |
| `create-release.sh` | `release.yml`, which publishes releases of this repository |

Jobs that need scripts check out `.github/scripts` from this repository at the
running workflow's own commit (`job.workflow_repository` and `job.workflow_sha`),
then move them to `$RUNNER_TEMP` so they never reach Docker build contexts,
scanners, or tests in the caller's workspace. Scripts read inputs only from
environment variables and fail with a `::error::` annotation on bad input.

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
    uses: diegocrew/action-devops/.github/workflows/allinone.yml@v0.5.0
    with:
      mode: audit
      python: true
      python-requirements: requirements-dev.txt
      python-command: python -m pytest
      docker: true
      terraform: true
      terraform-directory: infrastructure
```

Pin to a release tag, or to that tag's full commit SHA for production use; see
[releases](docs/releases/README.md) for versions and change logs. The workflow
checks out the **calling repository** at the event revision (including the PR
merge revision), not this repository. It runs on GitHub-hosted Ubuntu runners.

## Checks

All enabled checks run independently in parallel after configuration validation:
groups run in parallel, and so do the checks inside each group.

| Input | Default | Check |
| --- | --- | --- |
| `trivy` | `true` | Filesystem vulnerabilities, secrets, and IaC misconfiguration |
| `versions` | `true` | Renovate dependency lookups, including GitHub Actions, Terraform providers/modules, Docker images, and supported language dependencies |
| `lint` | `true` | Super-Linter's supported languages and configuration files |
| `python` | `false` | Python setup, optional requirements installation, and test command |
| `docker` | `false` | Docker build; never pushes an image |
| `terraform` | `false` | Recursive format check, backend-free init, and root-module validation; never plans or applies |
| `bicep` | `false` | Compiles every `.bicep` and `.bicepparam` file; never deploys |
| `cloudformation` | `false` | `cfn-lint` on YAML, JSON, and `.template` files |
| `iac-security` | `true` | Checkov security and best-practice checks for Terraform, CloudFormation, ARM, and Bicep |
| `codeql` | `false` | CodeQL `security-extended` analysis for one language, uploaded to code scanning |
| `dependabot` | `false` | Fails on open high/critical Dependabot alerts |
| `dependency-review` | `false` | Fails on newly introduced high/critical vulnerable dependencies; `pull_request` events only |
| `secret-scanning` | `false` | Fails on open secret-scanning alerts |

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
| `bicep-directory` | `bicep` | Directory searched recursively for Bicep files |
| `cloudformation-directory` | `cloudformation` | Directory searched recursively for CloudFormation templates |
| `codeql-language` | `javascript-typescript` | One of `javascript-typescript`, `python`, `ruby`, `c-cpp`, `go`, `java-kotlin`, `csharp`; call separately per language |

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

Invalid modes always fail. The final `summary` job reports each check's result by
group, including a group workflow that failed to start; tool details remain in
individual logs and dependency summaries.
Use the summary check for branch protection when using restrict mode.

### GitHub security features

`codeql` inherits the caller's `GITHUB_TOKEN`, so only callers that enable it
grant the extra permissions; everyone else keeps `contents: read`:

```yaml
jobs:
  checks:
    permissions:
      actions: read          # needed for private repositories
      contents: read
      security-events: write # upload to code scanning
    uses: diegocrew/action-devops/.github/workflows/allinone.yml@v0.5.0
    with:
      codeql: true
      codeql-language: python
```

Code scanning must be available for the repository (public, or GitHub Advanced
Security / Code Security enabled). Compiled languages use autobuild; use a
dedicated CodeQL workflow when autobuild cannot build the project. Swift is not
supported here because CodeQL Swift analysis requires macOS runners.

`dependabot` and `secret-scanning` read alert APIs that `GITHUB_TOKEN` cannot
access. Pass a fine-grained token restricted to the calling repository with only
**Dependabot alerts: read** and/or **Secret scanning alerts: read**:

```yaml
    secrets:
      github-security-token: ${{ secrets.SECURITY_ALERTS_TOKEN }}
```

A missing token fails the enabled check. These checks report existing alerts; they
do not change alert state. `dependency-review` needs the dependency graph enabled
and runs only for `pull_request` events.

### Advanced-mode credentials

Pass a dedicated bot token explicitly; normal checks need only `contents: read`
and do not need this secret:

```yaml
jobs:
  checks:
    uses: diegocrew/action-devops/.github/workflows/allinone.yml@v0.5.0
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
tests, package installation, Dockerfiles, Terraform providers, Bicep modules, and
repository linter configuration can execute or fetch repository-controlled code:
do not pass secrets or grant write permissions to these jobs. Every job sets
minimal permissions except `codeql`, which inherits the caller's token; only the
alert jobs, which do not check out code, receive `github-security-token`. `python-command` is intentionally a
shell command and must come from trusted workflow configuration, never event
titles, branch names, or other untrusted input.

Checkouts do not persist credentials. Script checkouts use the caller's
`GITHUB_TOKEN`, which can read this public repository. A caller's token cannot
read a private copy of this repository, so keep it public or the script checkout
fails. The separate advanced-mode bot job does
not check out or execute test code and disables Renovate package scripts and
post-upgrade commands. The caller must still trust the default branch and its
Renovate configuration. Third-party actions are pinned to commit SHAs; Renovate
can propose updates to those pins.