# Publishing Coactra

Coactra publishes one Python distribution: `coactra`.

The release branch flow is:

```text
feature/* -> dev -> release/x.y.z -> main -> tag v* -> PyPI
```

## Package Release

1. Merge finished feature branches into `dev`.
2. Create a release branch from `dev`.
3. Update `CHANGELOG.md`.
4. Open a pull request from the release branch into `main`.
5. Merge to `main`.
6. Tag the release with the new package version and push the tag:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The `.github/workflows/release.yml` workflow builds the source distribution and wheel,
then publishes to PyPI through Trusted Publishing when a `v*` tag is pushed.

PyPI Trusted Publisher settings must match the GitHub OIDC claims:

| Field | Value |
|---|---|
| Owner | `DataOpsFusion` |
| Repository | `coactra` |
| Workflow | `release.yml` |
| Environment | `pypi` |

PyPI rejects duplicate uploads for an existing version. The package version is
derived from the pushed Git tag via `hatch-vcs`; `v0.2.0` builds `coactra==0.2.0`.
Every release tag must be new, and release tags should not be moved after publishing.

The older `.github/workflows/workflow.yml` (push-to-main publish) is **disabled**.
Use tag-based `release.yml` only so releases are deliberate and not triggered by every
merge to `main`.

## Local Build Check

Run this before tagging. On an untagged commit, `hatch-vcs` may produce a development
version; the PyPI release version is finalized by the pushed `v*` tag.

```bash
rm -rf dist-all
(cd coactra && uv build --out-dir ../dist-all)
uvx twine check dist-all/*
```

## Documentation Release

The docs site is built with MkDocs Material.

```bash
python -m pip install mkdocs-material
mkdocs build --strict
```

`.github/workflows/docs.yml` builds docs for pushes and pull requests against
`dev` and `main`. Only pushes to `main` deploy the GitHub Pages site.

In GitHub Pages settings, use **GitHub Actions** as the build and deployment
source.

## Public API index

New stable symbols must be listed in [API_INDEX.md](../API_INDEX.md) before release.
See [maintainers/release-policy.md](../maintainers/release-policy.md) for the review checklist.
