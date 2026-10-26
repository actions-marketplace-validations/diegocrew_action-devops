# TODO: Additions and Improvements

The step-level action is the primary entry point; the reusable workflow remains
available for parallel jobs and per-check permissions. Prioritize tests and
reliability across both entry points before adding inputs. Items are proposals;
validate demand in a calling repository.

## 1. Correctness and Failure Reporting

- [ ] **Validate `mode` in direct group-workflow calls**: The action and
      [allinone.yml](../.github/workflows/allinone.yml) validate the mode, but callers may invoke a
      group workflow directly. Ensure a typo cannot silently act like `audit`, and test each direct
      group entry point.
- [ ] **Report failed Renovate lookups**: When
      [renovate-lookup.sh](../.github/scripts/renovate-lookup.sh) exits nonzero, the reporting step in
      [dependencies.yml](../.github/workflows/dependencies.yml) is skipped. Preserve a failed check
      while providing an actionable summary even when the report file is absent; test the failure path.
- [ ] **Consider validating the release index**:
      [create-release.sh](../.github/scripts/create-release.sh) checks for release notes but not their
      entry in [releases/README.md](releases/README.md). Decide whether a missing index entry should
      block publishing or merely be caught by a documentation check.

## 2. Reproducibility, Maintenance, and Performance

- [ ] **Set a reproducibility policy for tool versions**:
      [bicep-build.sh](../.github/scripts/bicep-build.sh) installs the latest Bicep CLI, while
      [iac.yml](../.github/workflows/iac.yml) defaults Terraform to `latest`; hosted-runner tools also
      change. Decide what to pin or expose as inputs, document the policy, and test pin updates. Do not
      claim all other tools are already pinned.
- [ ] **Reconsider the floating Renovate tag**: Renovate is pinned to the major tag `44` because it
      releases several times a day and exact pins failed the `versions` check within hours. The image
      can therefore change between runs. If reproducibility matters more, pin `@sha256:...` with
      automated digest updates.
- [ ] **Enable dependency updates for this repository**: No Renovate or Dependabot configuration is
      present. Choose an updater for pinned action SHAs and nonstandard tool versions, and enable
      Dependabot alerts in repository settings. Otherwise, SHA pins will become stale.
- [ ] **Cover nonstandard pins**: Default managers do not see versions inside scripts. Renovate does
      detect `renovate-version:` in [dependencies.yml](../.github/workflows/dependencies.yml) and
      [action.yml](../action.yml). Pins still needing custom managers or manual review: `checkov==...` in
      [checkov-scan.sh](../.github/scripts/checkov-scan.sh), `cfn-lint==...` in
      [cloudformation-lint.sh](../.github/scripts/cloudformation-lint.sh), and the
      `ghcr.io/renovatebot/renovate:...` tag in
      [renovate-lookup.sh](../.github/scripts/renovate-lookup.sh), which must stay in sync with
      `renovate-version:`. The "Pinned components" table in release notes is updated by nobody; decide
      whether to keep it or generate it. Verify extraction and update proposals rather than assuming a
      regular expression will find every pin.
- [ ] **Measure caching before adding it**: If cold installs are significant, configure
      dependency caching in setup steps for the reusable workflows and the action, not inside scan
      scripts. Preserve behavior when the optional Python requirements input is empty.
- [ ] **Consider configurable Super-Linter scope**: The action and
      [quality.yml](../.github/workflows/quality.yml) currently lint the full codebase. If callers
      need changed-file linting, add a shared input with the current behavior as its default and test
      pull-request and non-pull-request events for both entry points.
- [ ] **Reduce repeated script checkouts in the reusable workflows only if worthwhile**: The action
      runs scripts from `GITHUB_ACTION_PATH`; reusable-workflow jobs check out and move scripts. Any
      refactor must preserve the called workflow's commit pin and keep scripts out of caller build
      contexts and scanners. Also avoid deleting a caller's `.action-devops` directory during cleanup.

## 3. Optional Features (Demand-Driven)

- [ ] **Validate multi-root Terraform and CodeQL behavior**: Add tests for list parsing and
      per-language results; exercise the reusable workflow's language matrix and the action's
      documented restriction against mixing compiled and interpreted CodeQL languages. Avoid
      uploading real SARIF in test runs unless the fixture explicitly has the required permissions.
- [ ] **Optional SARIF uploads**: If callers have Code Scanning and grant the needed permissions,
      consider Trivy/Checkov uploads for both entry points. Keep default checks and summaries working
      without upload permissions.
- [ ] **Add Hadolint or Buildx only for a demonstrated caller need**: Keep the current Docker build
      behavior otherwise; additional tools increase setup time and maintenance.
