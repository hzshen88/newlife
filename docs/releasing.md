# Releasing proofroot and newlife

Both distributions are built from one tag and published by
`.github/workflows/release.yml`. The workflow tests both packages, builds wheels and
source distributions, checks their metadata and contents, installs the wheels into a
fresh environment, and exercises the complete external user-repository flow before any
OIDC credential is requested.

## The two-speed model

**GitHub holds history and moves continuously. PyPI holds releases and never moves.**
Ordinary pushes to `main` publish nothing and consume nothing — `release.yml` fires only
on a `v*` tag, and `lint.yml` is `workflow_dispatch` only. Cut a release when someone
outside needs a fix or a capability, not when enough commits have piled up.

Between releases `main` is ahead of what is on PyPI. That is normal; the two are told
apart by `newlife_source_sha256` in every artifact, not by the version string.

## One-time setup

**PyPI refuses two pending publishers with the same identity.** Registering the second
one returns:

    A pending trusted publisher matching this configuration has already been
    registered for a different project name.

So the two projects must differ in at least one field. This repository differs them by
environment, and `release.yml` has one publish job per environment:

| Field | proofroot | newlife |
|---|---|---|
| owner | `hzshen88` | `hzshen88` |
| repository | `newlife` | `newlife` |
| workflow | `release.yml` | `release.yml` |
| **environment** | **`pypi-proofroot`** | **`pypi-newlife`** |

No GitHub secret and no long-lived PyPI API token is required.

**A pending publisher does not reserve a project name** — PyPI creates the project only
on the first successful upload, and another user registering the name first invalidates
the pending publisher. Configure both entries immediately before the first release.

Creating the two GitHub environments by hand is optional (a workflow creates the one it
references on first use) and only necessary to add **required reviewers**, which pause
each upload until approved. On a private repository those protection rules need a paid
GitHub plan; without them the tag push itself is the only gate.

## Release

1. Bump the version in **both** `packages/proofroot/pyproject.toml` and
   `packages/newlife/pyproject.toml`:

       uv version --package proofroot 0.1.1 && uv version --package newlife 0.1.1

   `uv version` edits one package at a time, so this is two commands. Forgetting either
   makes `scripts/check_release_version.py` fail the build — loudly, but only after a
   wasted CI run.

2. If `proofroot` crosses a minor version, update the constraint `proofroot<0.2,>=0.1`
   in `packages/newlife/pyproject.toml` in the same commit. **Nothing checks this pairing
   automatically.**

3. Commit, merge to `main`, then create and push a matching tag:

       git tag -a v0.1.1 -F <message-file> && git push origin v0.1.1

   Write the message to a file rather than passing it inline: backticks in an inline
   `-m` are executed by the shell, which has silently eaten a line here before.

4. `publish-proofroot` runs first; `publish-newlife` needs it. That order is required —
   `newlife` depends on `proofroot`, so publishing `newlife` first leaves an
   uninstallable package on PyPI.

5. If one upload fails, re-run **only the failed job**. The jobs are separate precisely
   so a partial failure can be retried without re-uploading a version that already
   succeeded — PyPI rejects a duplicate version, and nothing here uses `skip-existing`
   to paper over that.

6. Verify from PyPI, not from the workflow's word:

       uv pip install newlife && newlife init <slug> && newlife freeze … && newlife audit …
