# action-devops

DevOps and security checks for GitHub Actions, available two ways:

- **Action** (`action.yml`): call it as a step, like any other action. Checks
  run one after another in your job.
- **Reusable workflow** (`.github/workflows/allinone.yml`): call it as a job.
  Checks run as parallel jobs, each with its own minimal permissions.

Both take the same check inputs, run the same checks and scripts, and share the same
modes and summary. Choose the action for simplicity, or the reusable workflow
for speed and per-check isolation.

The reusable workflow has three layers:

1. `.github/workflows/allinone.yml` is only configuration: it switches checks
   on or off and calls one reusable workflow per group.
2. Each group workflow in `.github/workflows/` runs its checks as parallel jobs.
3. Check logic lives in `.github/scripts/`, one script per check. Workflows
   only set up tools, pass inputs as environment variables, and call scripts
   or pinned actions.

Updating a check means editing its script, its group file, and the matching
step in `action.yml`, never the orchestrator.

| Workflow           | Checks                                                                                  |
| ------------------ | --------------------------------------------------------------------------------------- |
| `allinone.yml`     | Validates `mode`, calls the groups below in parallel, and summarizes                    |
| `quality.yml`      | `lint`                                                                                  |
| `build-test.yml`   | `python`, `docker`, `node`, `go`, `dotnet`                                              |
| `iac.yml`          | `terraform`, `tflint`, `bicep`, `cloudformation`                                        |
| `security.yml`     | `trivy`, `iac-security`, `codeql`, `dependabot`, `dependency-review`, `secret-scanning` |
| `dependencies.yml` | `versions`, plus advanced-mode fix PRs                                                  |

A group with every check off is skipped. `allinone.yml` calls the groups with
`$/.github/workflows/...`, which resolves to this repository at the same commit,
so pinning `allinone.yml` to a SHA pins every group too. Each group can also be
called directly with the same inputs.

| Script                                                                           | Used by                                                          |
| -------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `validate-config.sh`                                                             | `allinone.yml` configuration                                     |
| `summarize.py`                                                                   | `allinone.yml` summary                                           |
| `action-results.py`                                                              | `action.yml` summary                                             |
| `python-tests.sh`, `docker-build.sh`, `run-command.sh`                           | `build-test.yml`                                                 |
| `terraform-validate.sh`, `tflint.sh`, `bicep-build.sh`, `cloudformation-lint.sh` | `iac.yml`                                                        |
| `checkov-scan.sh`, `codeql-language.sh`, `codeql-results.py`, `github-alerts.sh` | `security.yml`                                                   |
| `list.sh`                                                                        | Sourced by scripts that accept comma- or newline-separated lists |
| `runtime.sh`                                                                     | Shared runner-path and Python virtualenv handling                |
| `validate-platform.sh`                                                           | Rejects Linux-only checks on other composite-action runners     |
| `renovate-lookup.sh`, `renovate-report.py`                                       | `dependencies.yml`                                               |
| `create-release.sh`                                                              | `release.yml`, which publishes releases of this repository       |

Jobs that need scripts check out `.github/scripts` from this repository at the
running workflow's own commit (`job.workflow_repository` and `job.workflow_sha`),
then move them to `$RUNNER_TEMP` so they never reach Docker build contexts,
scanners, or tests in the caller's workspace. Scripts read inputs only from
environment variables and fail with a `::error::` annotation on bad input.

## Use from any repository

### As an action

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
    runs-on: ubuntu-latest
    steps:
      - uses: diegocrew/action-devops@v1.0.0
        with:
          mode: audit
          python: true
          python-requirements: requirements-dev.txt
          python-command: python -m pytest
          docker: true
          terraform: true
          terraform-directory: infrastructure
```

The action checks out the calling repository itself; set `checkout: false` if
the job already did, with `fetch-depth: 0`. Tokens are passed as inputs
(`github-security-token`, `renovate-token`) instead of secrets.

Differences from the reusable workflow:

- Checks run **one after another in the calling job**, not as parallel jobs, so
  a full run takes longer.
- All checks share the job's permissions and tools. Grant only what enabled
  checks need (for example `security-events: write` only with `codeql`), and do
  not pass `github-security-token` or `renovate-token` to a job that also runs
  repository code you do not trust.
- `codeql-language` cannot mix compiled (`c-cpp`, `go`, `java-kotlin`, `csharp`)
  and interpreted (`javascript-typescript`, `python`, `ruby`) languages in one
  call; use two steps or the reusable workflow.
- Modes behave the same: each check tolerates failure, and the final summary
  step fails the job only in `restrict` mode or on invalid configuration.

### As a reusable workflow

```yaml
jobs:
  checks:
    uses: diegocrew/action-devops/.github/workflows/allinone.yml@v1.0.0
    with:
      mode: audit
      python: true
      python-command: python -m pytest
```

Pin to a release tag, or to that tag's full commit SHA for production use; see
[releases](docs/releases/README.md) for versions and changelogs. Both entry
points check out the **calling repository** at the event revision (including the
PR merge revision), not this repository.

### Platform requirements

- **github.com only.** The groups are called with `$/` self-repository references
  and check out scripts using `job.workflow_repository` and `job.workflow_sha`;
  neither is available on GitHub Enterprise Server.
- **GitHub-hosted Ubuntu, macOS, and Windows runners.** Reusable workflows accept
  `runner` (default `ubuntu-latest`) for portable checks. The action uses the
  calling job's runner. `$/` references need runner 2.336.0 or newer, which hosted
  runners already have. Self-hosted runners and custom images are not certified.
- **This repository must stay public**, because script checkouts use the caller's
  token (see [Security boundaries](#security-boundaries)).

| Checks | Reusable workflow | Composite action |
| --- | --- | --- |
| Python, Node.js, Go, .NET, Terraform, TFLint, Bicep, CloudFormation, Checkov, CodeQL, alert APIs, dependency review | Selected `runner` | Calling runner |
| Super-Linter, Docker builds, Trivy integration, Renovate lookups and fix PRs | Always Ubuntu | Linux only |
| Configuration, language-matrix preparation, result aggregation | Always Ubuntu | Calling runner |

Linux-only integrations stay on Ubuntu even when `runner` is `macos-latest` or
`windows-latest`. Direct callers of `build-test.yml`, `iac.yml`, and `security.yml`
can also set `runner`. Quality and dependency workflows remain Ubuntu-only.
CodeQL's upstream language and architecture restrictions still apply; custom
build/test commands must be compatible with the selected OS.

The composite action rejects an enabled Linux-only check on macOS/Windows as an
invalid configuration, even in audit mode. Disable `lint`, `trivy`, and `versions`
(all enabled by default), and leave `docker` disabled:

```yaml
jobs:
  checks:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: diegocrew/action-devops@v1.0.0
        with:
          lint: "false"
          trivy: "false"
          versions: "false"
          terraform: "true"
```

For the reusable workflow, set `with: { runner: windows-latest }` instead; no
Linux-only checks need to be disabled. Ubuntu remains the default. Scripts use
Bash, including Git Bash on Windows and the system Bash on macOS. Python is
provisioned explicitly for internal tools (3.12), independently of
`python-version` for the caller's tests. Bicep uses the pinned standalone CLI
(v0.48.1), without requiring Azure CLI or Azure credentials.

## Checks

In the reusable workflow, all enabled checks run independently in parallel after
configuration validation. The action runs the same checks in sequence.

| Input               | Default | Check                                                                                                                                  |
| ------------------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `trivy`             | `true`  | Filesystem vulnerabilities, secrets, and IaC misconfiguration                                                                          |
| `versions`          | `true`  | Renovate dependency lookups, including GitHub Actions, Terraform providers/modules, Docker images, and supported language dependencies |
| `lint`              | `true`  | Super-Linter's supported languages and configuration files                                                                             |
| `python`            | `false` | Python setup, optional requirements installation, and test command                                                                     |
| `docker`            | `false` | Docker build; never pushes an image                                                                                                    |
| `node`              | `false` | Node.js setup and build/test command                                                                                                   |
| `go`                | `false` | Go setup and build/test command                                                                                                        |
| `dotnet`            | `false` | .NET SDK setup and build/test command                                                                                                  |
| `terraform`         | `false` | Recursive format check, backend-free init, and validation of each root module; never plans or applies                                  |
| `tflint`            | `false` | TFLint on each Terraform root module, using its `.tflint.hcl` if present                                                               |
| `bicep`             | `false` | Compiles every `.bicep` and `.bicepparam` file; never deploys                                                                          |
| `cloudformation`    | `false` | `cfn-lint` on YAML, JSON, and `.template` files                                                                                        |
| `iac-security`      | `true`  | Checkov security and best-practice checks for Terraform, CloudFormation, ARM, Bicep, and workflows                                     |
| `codeql`            | `false` | CodeQL `security-extended` analysis for each listed language, uploaded to code scanning                                                |
| `dependabot`        | `false` | Fails on open high/critical Dependabot alerts                                                                                          |
| `dependency-review` | `false` | Fails on newly introduced high/critical vulnerable dependencies; `pull_request` events only                                            |
| `secret-scanning`   | `false` | Fails on open secret-scanning alerts                                                                                                   |

Set any check to `false` to skip it. Enable project-specific checks only when their
files exist; missing explicitly requested files are errors, not silent skips.
Configure Super-Linter using its standard repository configuration files.
Version checks use Renovate's supported managers and respect repository Renovate
configuration; ignored, disabled, unsupported, or unresolvable dependencies cannot
be guaranteed current. Available updates and lookup errors fail the version check.
No infrastructure credentials are supplied.

| Additional input           | Default                          | Purpose                                                                                                               |
| -------------------------- | -------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `mode`                     | `audit`                          | Failure/remediation policy below                                                                                      |
| `severity`                 | `HIGH,CRITICAL`                  | Trivy severity threshold                                                                                              |
| `python-version`           | `3.12`                           | Python interpreter version                                                                                            |
| `python-requirements`      | empty                            | Requirements file to install; empty skips installation                                                                |
| `python-command`           | `python -m unittest discover -v` | Test shell command; install pytest in your requirements if using the example                                          |
| `docker-context`           | `.`                              | Docker build context                                                                                                  |
| `dockerfile`               | `Dockerfile`                     | Dockerfile path relative to repository root                                                                           |
| `node-version`             | `24`                             | Node.js version for `actions/setup-node`                                                                              |
| `node-command`             | `npm ci && npm test`             | Trusted build/test shell command; `cd` first for a subdirectory                                                       |
| `go-version`               | empty                            | Go version; empty reads it from `go.mod` at the repository root                                                       |
| `go-command`               | `go vet ./... && go test ./...`  | Trusted build/test shell command                                                                                      |
| `dotnet-version`           | `10.0.x`                         | .NET SDK version for `actions/setup-dotnet`                                                                           |
| `dotnet-command`           | `dotnet test`                    | Trusted build/test shell command                                                                                      |
| `terraform-directory`      | `.`                              | Root module directories, comma- or newline-separated; used by `terraform` and `tflint`                                |
| `terraform-version`        | `latest`                         | Terraform CLI version; pin for reproducible runs                                                                      |
| `tflint-version`           | `v0.65.0`                        | TFLint version                                                                                                        |
| `bicep-directory`          | `bicep`                          | Directory searched recursively for Bicep files                                                                        |
| `cloudformation-directory` | `cloudformation`                 | Directory searched recursively for CloudFormation templates                                                           |
| `codeql-language`          | `javascript-typescript`          | Comma- or newline-separated list of `javascript-typescript`, `python`, `ruby`, `c-cpp`, `go`, `java-kotlin`, `csharp` |

### Multiple Terraform roots and CodeQL languages

`terraform-directory` and `codeql-language` accept lists; a single value behaves
as before:

```yaml
with:
  terraform: true
  tflint: true
  terraform-directory: |
    infrastructure/network
    infrastructure/app
  codeql: true
  codeql-language: python, javascript-typescript
```

Terraform roots are checked one after another in a single job. Every root runs
even if an earlier one fails, and the job summary lists each root's result.
CodeQL runs one parallel job per language; the `codeql` result fails if any
language does not succeed, and its job summary lists each language.

TFLint uses each root's `.tflint.hcl`. Without one, only the bundled Terraform
ruleset runs; add a provider plugin (for example AWS, Azure, or Google) in that file.

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

Invalid modes always fail. The final `summary` job shows the active mode and
reports each check's result by group, including a group workflow that failed to
start. Failures tolerated in `audit` or `advanced` mode are labeled as such, never
as passed. Tool details remain in individual logs and job summaries.
Use the summary check for branch protection when using restrict mode.

### GitHub security features

`codeql` inherits the caller's `GITHUB_TOKEN`, so only callers that enable it
grant the extra permissions; everyone else keeps `contents: read`:

```yaml
jobs:
  checks:
    permissions:
      actions: read # needed for private repositories
      contents: read
      security-events: write # upload to code scanning
    uses: diegocrew/action-devops/.github/workflows/allinone.yml@v1.0.0
    with:
      codeql: true
      codeql-language: python
```

With the action, grant the same permissions to the job that runs it.

Code scanning must be available for the repository (public, or GitHub Advanced
Security / Code Security enabled). Compiled languages use autobuild; use a
dedicated CodeQL workflow when autobuild cannot build the project. Swift is not
exposed by this project's language allowlist; use a dedicated CodeQL workflow on
macOS for Swift analysis.

`dependabot` and `secret-scanning` read alert APIs that `GITHUB_TOKEN` cannot
access. Pass a fine-grained token restricted to the calling repository with only
**Dependabot alerts: read** and/or **Secret scanning alerts: read**:

```yaml
secrets:
  github-security-token: ${{ secrets.SECURITY_ALERTS_TOKEN }}
```

A missing token fails the enabled check. These checks report existing alerts; they
do not change alert state. `dependency-review` needs the dependency graph enabled
and runs only for `pull_request` events. On other events it shows as `skipped` in
the summary. If it is the only security check enabled, the security group still
starts but runs no checks; that is expected.

### Advanced-mode credentials

Pass a dedicated bot token explicitly; normal checks need only `contents: read`
and do not need this secret:

```yaml
jobs:
  checks:
    uses: diegocrew/action-devops/.github/workflows/allinone.yml@v1.0.0
    with:
      mode: advanced
    secrets:
      renovate-token: ${{ secrets.RENOVATE_TOKEN }}
```

With the action, pass it as `renovate-token: ${{ secrets.RENOVATE_TOKEN }}`
under `with:`.

Use a GitHub App installation token or fine-grained PAT restricted to the calling
repository, with contents and pull requests write access, issues write access
if using Renovate's dependency dashboard, and workflows write access for Actions
updates. Organization policies must allow bot PR creation. Missing credentials
or failed PR attempts are reported but remain non-blocking. Review generated PRs;
not every finding has an automated fix. Existing Renovate schedules, package
rules, and PR limits may defer updates.

## Security boundaries

Use `pull_request`, not `pull_request_target`, to test untrusted changes. Python,
Node.js, Go, and .NET builds and tests, package installation, Dockerfiles,
Terraform providers, TFLint plugins, Bicep modules, and repository linter
configuration can execute or fetch repository-controlled code:
do not pass secrets or grant write permissions to these jobs. Every job sets
minimal permissions except the CodeQL analysis jobs, which inherit the caller's token; only the
alert jobs, which do not check out code, receive `github-security-token`. The
`*-command` inputs are intentionally shell commands and must come from trusted
workflow configuration, never event titles, branch names, or other untrusted input.
TFLint receives the read-only `GITHUB_TOKEN` only while downloading plugins, not
while running them.

Checkouts do not persist credentials. Script checkouts use the caller's
`GITHUB_TOKEN`, which can read this public repository. A caller's token cannot
read a private copy of this repository, so keep it public or the script checkout
fails. The separate advanced-mode bot job does
not check out or execute test code and disables Renovate package scripts and
post-upgrade commands. The caller must still trust the default branch and its
Renovate configuration. Third-party actions are pinned to commit SHAs; Renovate
can propose updates to those pins.

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Contributing and license

See [CONTRIBUTING.md](CONTRIBUTING.md). Licensed under the [MIT License](LICENSE).
