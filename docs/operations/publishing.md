# Publishing Coactra

Coactra publishes one Python distribution: `coactra`.

The release branch flow is:

```text
feature/* -> dev -> release/x.y.z -> main -> PyPI
```

## Package Release

1. Merge finished feature branches into `dev`.
2. Create a release branch from `dev`.
3. Bump `coactra/pyproject.toml`.
4. Update `CHANGELOG.md`.
5. Open a pull request from the release branch into `main`.
6. Merge to `main`.

The `.github/workflows/release.yml` workflow builds the source distribution and
wheel, then publishes to PyPI through Trusted Publishing.

PyPI Trusted Publisher settings must match the GitHub OIDC claims:

| Field | Value |
|---|---|
| Owner | `DataOpsFusion` |
| Repository | `coactra` |
| Workflow | `release.yml` |
| Environment | `pypi` |

PyPI rejects duplicate uploads for an existing version. Every merge to `main`
that triggers publishing must carry a new version.

## Local Build Check

Run this before opening the release pull request:

```bash
make type
make release-check
rm -rf dist-all
(cd coactra && uv build --out-dir ../dist-all)
uvx twine check dist-all/*
```

`make release-check` covers lint, compile, the default non-live test suite, docs,
examples, clean wheel/sdist install validation, stale-path scanning, live-backend
inventory, and whitespace checks. `make type` is separate and must run from an
environment with the development extra installed.

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
