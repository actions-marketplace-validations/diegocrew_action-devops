# TODO: Additions and Improvements

Prioritize proving existing behavior before expanding the public workflow interface.
Items below are proposals, not commitments; validate impact in a calling repository.

## 1. Validate the Existing Workflows (Highest Priority)

- [x] **Dogfood the current workflows**: [ci.yml](../.github/workflows/ci.yml) runs
      [allinone.yml](../.github/workflows/allinone.yml) from the current commit in `audit` mode on pull
      requests, pushes to `main`, and manual dispatch. The first run (PR #8, run 40238862617) proved the
      `$/` group calls, script checkout, `job.status` outputs, and summary end-to-end.
      [actionlint.yml](../.github/linters/actionlint.yml) suppresses only actionlint's `$/` and
      `job.workflow_*` false positives. Consider a scheduled run only if its cost and signal justify it.
- [x] **Make this repository pass its own lint checks**: Fixed the findings from the first dogfood
      runs: formatting (Black, Ruff, shfmt, Prettier), pylint and flake8, Markdown line length,
      terminology, zizmor, and a non-executable `list.sh`. Deliberate patterns are configured with
      reasons in `.github/linters/`: JSCPD ignores workflow YAML, whose repetition is structural
      (`allinone.yml` redeclares every group input and each job checks out its own scripts), and Checkov
      skips CKV2_GHA_1 because `allinone.yml` and `security.yml` must omit top-level permissions;
      Checkov ignores inline skips for that check. `.editorconfig` sets `shfmt` to 2-space indentation.
- [ ] **Make the `versions` check pass, then consider `restrict`**: The first runs reported 2
      updates (Renovate 44.167.5 and `actions/dependency-review-action` v4, both now updated) and 1
      lookup error whose details went only to the job summary.
      [renovate-report.py](../.github/scripts/renovate-report.py) now also prints every update and error
      to the job log; read the next run's log and fix or configure the lookup error. Once `lint` and
      `versions` pass, consider `restrict` mode for CI.
- [ ] **Test status propagation and policy on GitHub Actions**: Exercise successful, failed, and
      skipped checks; verify the outputs from group jobs using `${{ job.status }}`, the final summary,
      and `audit`, `restrict`, and `advanced` behavior. Use isolated/controlled failing fixtures rather
      than making normal PR CI fail. Unit tests with fabricated `needs` JSON do not prove
      reusable-workflow wiring.
- [ ] **Add Python unit tests**: Cover JSON parsing, missing or malformed reports, Markdown output,
      and exit codes in [summarize.py](../.github/scripts/summarize.py),
      [codeql-results.py](../.github/scripts/codeql-results.py), and
      [renovate-report.py](../.github/scripts/renovate-report.py). `renovate-report.py` does not
      implement modes; test modes only for `summarize.py`. Run tests in CI, either directly or through
      the `python` check with an explicit test command.
- [ ] **Add shell-script fixture tests**: Cover valid and invalid inputs and failure paths for
      [validate-config.sh](../.github/scripts/validate-config.sh),
      [codeql-language.sh](../.github/scripts/codeql-language.sh),
      [list.sh](../.github/scripts/list.sh),
      [terraform-validate.sh](../.github/scripts/terraform-validate.sh) and
      [tflint.sh](../.github/scripts/tflint.sh) (multiple roots, one failing root, missing directory),
      [run-command.sh](../.github/scripts/run-command.sh),
      [github-alerts.sh](../.github/scripts/github-alerts.sh), and
      [create-release.sh](../.github/scripts/create-release.sh), mocking `terraform`, `tflint`, and
      `gh`. These cases were exercised once with throwaway mocks when list support was added; make them
      a committed suite.
- [ ] **Finish validating the release path**: The live path is already proven: the `v0.5.0` tag push
      ran [release.yml](../.github/workflows/release.yml) successfully (run 40106403947), and the
      `workflow_dispatch` republish from `main` after PR #6 also succeeded (run 40106745440), so the
      published release carries the current notes. What remains is testing
      [create-release.sh](../.github/scripts/create-release.sh) with mocked `gh` for the invalid-tag,
      missing-notes, create, and edit branches. GitHub's tag-filter syntax supports `+` in the current
      `v[0-9]+.[0-9]+.[0-9]+` pattern; do not replace it on the assumption that `+` is a
      regular-expression-only operator.

## 2. Correctness and Failure Reporting

- [ ] **Validate `mode` in direct group calls**: [README.md](../README.md) advertises calling group
      workflows directly, but only [allinone.yml](../.github/workflows/allinone.yml) uses
      [validate-config.sh](../.github/scripts/validate-config.sh). A typo passed to a group currently
      acts like `audit` because its jobs use `inputs.mode != 'restrict'`. Make invalid modes fail for
      direct callers too, and test each group.
- [ ] **Report failed Renovate lookups**: When
      [renovate-lookup.sh](../.github/scripts/renovate-lookup.sh) exits nonzero, the reporting step in
      [dependencies.yml](../.github/workflows/dependencies.yml) is skipped. Preserve a failed check
      while providing an actionable summary even when the report file is absent; test the failure path.
- [ ] **Consider validating the release index**:
      [create-release.sh](../.github/scripts/create-release.sh) checks for release notes but not their
      entry in [releases/README.md](releases/README.md). Decide whether a missing index entry should
      block publishing or merely be caught by a documentation check.

## 3. Reproducibility, Maintenance, and Performance

- [ ] **Set a reproducibility policy for tool versions**:
      [bicep-build.sh](../.github/scripts/bicep-build.sh) installs the latest Bicep CLI, while
      [iac.yml](../.github/workflows/iac.yml) defaults Terraform to `latest`; hosted-runner tools also
      change. Decide what to pin or expose as inputs, document the policy, and test pin updates. Do not
      claim all other tools are already pinned.
- [ ] **Consider a Renovate image digest**:
      [renovate-lookup.sh](../.github/scripts/renovate-lookup.sh) uses a versioned Docker tag, not an
      immutable image digest. If pinning to `@sha256:...`, arrange automated digest updates so it does
      not become stale.
- [ ] **Enable dependency updates for this repository**: Nothing updates the pinned action SHAs
      today: there is no `renovate.json` or `dependabot.yml`, Dependabot alerts are not enabled, and no
      bot has opened a PR. Choose Renovate (app installation plus config) or Dependabot
      (`github-actions` ecosystem) and enable Dependabot alerts in repository settings. Without this,
      the "pinned to commit SHAs" claim decays into "pinned to old commits".
- [ ] **Cover nonstandard pins**: Default managers do not see versions inside scripts. Renovate does
      detect `renovate-version:` in [dependencies.yml](../.github/workflows/dependencies.yml) (it
      proposed 44.181.6). Pins still needing custom managers or manual review: `checkov==...` in
      [checkov-scan.sh](../.github/scripts/checkov-scan.sh), `cfn-lint==...` in
      [cloudformation-lint.sh](../.github/scripts/cloudformation-lint.sh), and the
      `ghcr.io/renovatebot/renovate:...` tag in
      [renovate-lookup.sh](../.github/scripts/renovate-lookup.sh), which must stay in sync with
      `renovate-version:`. The "Pinned components" table in release notes is updated by nobody; decide
      whether to keep it or generate it. Verify extraction and update proposals rather than assuming a
      regular expression will find every pin.
- [ ] **Measure caching before adding it**: If cold installs are significant, configure
      pip/dependency caching in the relevant workflow setup for
      [build-test.yml](../.github/workflows/build-test.yml),
      [security.yml](../.github/workflows/security.yml), and [iac.yml](../.github/workflows/iac.yml),
      not inside the scan scripts. Handle an empty optional requirements file. Adding
      `--disable-pip-version-check` to [python-tests.sh](../.github/scripts/python-tests.sh) is
      separate, low-priority cleanup.
- [ ] **Consider configurable Super-Linter scope**: [quality.yml](../.github/workflows/quality.yml)
      hardcodes `VALIDATE_ALL_CODEBASE: true`. If callers need changed-file linting, add an input
      (defaulting to current behavior), forward it through
      [allinone.yml](../.github/workflows/allinone.yml), and test PR and non-PR behavior.
- [ ] **Consider reducing repeated script checkouts**: The checkout/move sequence appears in 12
      jobs. Refactor only if it preserves the called workflow's commit pin and keeps scripts out of
      caller build contexts and scanners. Skipping a move in jobs without caller checkout is a minor
      optimization, not a separate priority. While there, use a less collision-prone checkout path: `rm
-rf .action-devops` runs inside the caller's workspace and would delete a caller directory of the
      same name.

## 4. Optional Features (Demand-Driven)

- [x] **Multiple CodeQL languages and Terraform roots**: `codeql-language` and `terraform-directory`
      accept comma- or newline-separated lists; single values behave as before. CodeQL uses a matrix
      with per-language result outputs and a `codeql` result job; Terraform roots run sequentially in
      one job, all roots always run, and the job summary lists each. Still untested on GitHub Actions;
      covered by the status-propagation item in section 1.
- [x] **Additional build and test ecosystems**: `node`, `go`, and `dotnet` checks in
      [build-test.yml](../.github/workflows/build-test.yml), each a toolchain setup plus a trusted
      command via [run-command.sh](../.github/scripts/run-command.sh). Still open: Hadolint (consider
      separately) and switching [docker-build.sh](../.github/scripts/docker-build.sh) to Buildx (only
      for a concrete build requirement).
- [x] **Optional `tflint` check**: In [iac.yml](../.github/workflows/iac.yml), pinned by
      `tflint-version`, configured by each root's `.tflint.hcl`; fails on any finding; runs on every
      root in `terraform-directory`.
- [ ] **Optional SARIF uploads**: If callers have Code Scanning and grant the needed permissions,
      consider Trivy/Checkov SARIF uploads in [security.yml](../.github/workflows/security.yml). Keep
      the default read-only checks and summaries working without uploads.
- [x] **Improve the human-readable summary**: [summarize.py](../.github/scripts/summarize.py) shows
      the mode and its policy, labeled results, failures marked as tolerated in `audit`/`advanced` mode,
      and a failed-check list.
- [x] **Document dependency-review on non-PR events**: Documented in [README.md](../README.md); the
      group condition is unchanged.
- [x] **Document platform limits in `README.md`**: Added a "Platform requirements" section.

## 5. Repository Governance

- [x] **Choose and add an open-source license**: MIT, in [LICENSE](../LICENSE).
- [x] **Add `SECURITY.md` and `CONTRIBUTING.md`**: [SECURITY.md](../SECURITY.md) routes reports
      through GitHub private vulnerability reporting (now enabled);
      [CONTRIBUTING.md](../CONTRIBUTING.md) has the change checklist and local shellcheck/actionlint
      commands. Update its "Validate locally" section once tests exist.
- [x] **Require the dogfood `summary` check on `main`**: The "Protect main" ruleset (ID 25838214)
      blocks deletion and force pushes, requires pull requests (zero approvals), and requires the
      `checks / summary` status check from GitHub Actions. In `audit` mode that check fails only on
      invalid configuration or broken workflow wiring; it becomes a quality gate once CI moves to
      `restrict`.
