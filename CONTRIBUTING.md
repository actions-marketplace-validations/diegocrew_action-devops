# Contributing

Changes land on `main` through pull requests. Report security issues privately;
see [SECURITY.md](SECURITY.md).

## Where changes go

The repository has three layers (see [README.md](README.md)):

| Change | Edit |
| --- | --- |
| How a check works | Its script in `.github/scripts/` |
| Tool setup, permissions, or a new check in a group | The group workflow in `.github/workflows/` |
| A new input or check that callers can switch | The group workflow **and** `allinone.yml`, which forwards it |

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
- [ ] [README.md](README.md) input, check, and script tables are updated.
- [ ] User-visible changes are noted for the next release in
      [docs/releases](docs/releases/README.md).

## Validate locally

There is no automated test suite yet; run these before opening a pull request:

```bash
shellcheck .github/scripts/*.sh
python3 -m py_compile .github/scripts/*.py
actionlint
```

actionlint v1.7.12 does not recognize `$/` workflow references or the
`job.workflow_repository` and `job.workflow_sha` fields and reports them as
errors; ignore those specific errors and fix everything else.

Then run the workflows from a test repository that calls your branch, starting
with `mode: audit`.

## Releases

Maintainers publish releases by following
[Publishing a release](docs/releases/README.md#publishing-a-release).

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
