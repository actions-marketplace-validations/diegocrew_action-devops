# Releases

Each release has its own notes file, `vMAJOR.MINOR.PATCH.md`, which is also the
body of its GitHub release page.

| Version | Date | Summary |
| --- | --- | --- |
| [v0.5.0](v0.5.0.md) | 2026-10-24 | First release: configurable all-in-one checks in grouped workflows backed by scripts |

## Versioning

Versions follow [Semantic Versioning](https://semver.org/). Before `v1.0.0`, a
minor version (`v0.6.0`) may change inputs or behavior; a patch version
(`v0.5.1`) only fixes bugs or updates pinned tools without changing inputs.

Pin callers to a release tag, or better, to the tag's full commit SHA:

```yaml
uses: diegocrew/action-devops/.github/workflows/allinone.yml@v0.5.0
```

## Publishing a release

1. Add `docs/releases/vX.Y.Z.md` using the sections below, add it to the table
   above, and merge to `main`.
2. Tag the merge commit and push the tag:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z" <merge-commit-sha>
   git push origin vX.Y.Z
   ```

3. The `Release` workflow (`.github/workflows/release.yml`) creates the GitHub
   release from the notes file. Pushing a tag without a notes file fails the
   workflow. Re-running it after editing the notes updates the release text.

## Notes template

```markdown
# vX.Y.Z

One-paragraph summary.

## New features
## Changed
## Fixed
## Security
## Deprecated / removed
## Known limitations
## Upgrading
```

Leave out empty sections.
