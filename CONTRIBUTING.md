# Contributing

Changes land on `main` through pull requests. Report security issues privately;
see [SECURITY.md](SECURITY.md).

## Where changes go

The repository has three layers (see [README.md](README.md)):

| Change                                             | Edit                                                         |
| -------------------------------------------------- | ------------------------------------------------------------ |
| How a check works                                  | Its script in `.github/scripts/`                             |
| Tool setup, permissions, or a new check in a group | The group workflow in `.github/workflows/`                   |
| A new input or check that callers can switch       | The group workflow **and** `allinone.yml`, which forwards it |

Keep logic in scripts. Workflows only set up tools, pass inputs as environment
variables, and call scripts or pinned actions.

## Checklist

- [ ] Scripts read inputs only from environment variables, use
      `set -euo pipefail`, and fail with a `::error::` annotation on bad input.
- [ ] New `.sh` scripts are executable: `git update-index --chmod=+x <file>`.
- [ ] Each job sets minimal `permissions` and checks out with
      `persist-credentials: false`.
- [ ] Third-party actions are pinned to a full commit SHA with a version comment;
      tools installed by scripts are pinned to exact versions.
- [ ] Every input in a group workflow is also declared and forwarded in
      `allinone.yml`, and every check job exposes `result: ${{ job.status }}`
      as a group output so the summary can report it.
- [ ] Every check job in a group workflow has `needs: mode`, so direct callers
      cannot run checks with an invalid mode.
- [ ] [README.md](README.md) input, check, and script tables are updated.
- [ ] User-visible changes are noted for the next release in
      [docs/releases](docs/releases/README.md).

## Validate locally

The `CI` workflow runs this repository's own checks on every pull request. Before
opening one, run:

```bash
python3 -m unittest discover -s tests -v
shellcheck -x .github/scripts/*.sh
python3 -m py_compile .github/scripts/*.py
actionlint -config-file .github/linters/actionlint.yml
```

[`.github/linters/actionlint.yml`](.github/linters/actionlint.yml) ignores only
the errors actionlint v1.7.12 reports for `$/` workflow references and the
`job.workflow_repository` and `job.workflow_sha` fields, which GitHub supports
but actionlint does not yet recognize. Super-Linter reads the same file.

actionlint cannot follow `$/` calls, so it does not check the inputs that
`allinone.yml` passes to the group workflows. Compare them by hand: every group
input must be declared in `allinone.yml` with the same default and forwarded.

Then run the workflows from a test repository that calls your branch, starting
with `mode: audit`.

## Cross-platform checks

CI runs the reusable workflow and composite action on `ubuntu-latest`,
`macos-latest`, and `windows-latest`, including real Terraform, TFLint, Bicep,
CloudFormation executions against fixtures in `tests/fixtures/iac`, and controlled
Checkov findings in `tests/fixtures/checkov` (never deployed).
It also verifies audit/restrict failure propagation and rejection of Linux-only
checks in the composite action.

Keep portable scripts compatible with macOS's system Bash 3.2 and Windows Git
Bash. Use `runtime.sh` for virtualenv paths (`bin` versus `Scripts`) and native
Windows runner-temp conversion. `.gitattributes` enforces LF shell scripts.
The portable tests in `tests/test_platforms.py` must run on Windows; the older
POSIX executable-stub fixtures are intentionally skipped there. New portable jobs
must use and forward `runner`, while Linux-only integrations and control jobs stay
on Ubuntu.

## Releases

Maintainers publish releases by following
[Publishing a release](docs/releases/README.md#publishing-a-release).

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
