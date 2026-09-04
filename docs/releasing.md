# Releasing proofroot and newlife

Both distributions are built from one tag and published by
`.github/workflows/release.yml`. The workflow tests both packages, builds wheels and
source distributions, checks their metadata and contents, installs the wheels into a
fresh environment, and exercises the complete external user-repository flow before any
OIDC credential is requested.

## One-time setup

1. Create a GitHub environment named `pypi`. Add required reviewers and restrict it to
   protected release tags if the repository settings available to you support those
   controls.
2. In PyPI, add the same GitHub Trusted Publisher to both the `proofroot` and `newlife`
   projects. For a first release, create two pending publishers. Use:

   - owner: `hzshen88`
   - repository: `newlife`
   - workflow: `release.yml`
   - environment: `pypi`

No GitHub secret or long-lived PyPI API token is required. A pending publisher does not
reserve a project name, so configure both entries immediately before the first release.

## Release

1. Set the same release version in `packages/proofroot/pyproject.toml` and
   `packages/newlife/pyproject.toml`.
2. Run the local checks documented in the repository README and merge the release commit
   to `main`.
3. Create and push a matching tag, for example `v0.1.0` for package version `0.1.0`.
4. Approve the `pypi` environment deployment after the build job is green.
5. Verify both project pages and install both packages from PyPI in a fresh environment.

The workflow rejects a tag that does not match both package versions. It uploads both
projects in one publishing step; PyPI scopes the short-lived token to every project that
registered this exact publisher identity.
