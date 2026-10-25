# Security policy

## Supported versions

Only the latest release receives fixes. See [releases](docs/releases/README.md).
Callers pinned to an older tag or SHA must upgrade to get a fix.

## Reporting a vulnerability

Do not open a public issue. Report privately through
[GitHub private vulnerability reporting](https://github.com/diegocrew/action-devops/security/advisories/new)
(Security tab → Report a vulnerability).

Include the affected workflow or script, the release or commit, the calling
configuration needed to reproduce, and the impact. Fixes ship as a patch release
with a GitHub security advisory.

## Scope

In scope: anything in this repository that a caller runs, for example

- token or secret exposure, or permissions broader than documented;
- untrusted input (pull request content, branch names, inputs) reaching a shell
  or a privileged job;
- a way for the calling repository's content to alter which scripts or workflows
  run, bypassing the commit pin;
- checks that silently pass when they should fail.

Out of scope: vulnerabilities in third-party tools and actions (report them
upstream), and findings these checks report in a caller's own code.
The intended trust boundaries are described under
[Security boundaries](README.md#security-boundaries).
