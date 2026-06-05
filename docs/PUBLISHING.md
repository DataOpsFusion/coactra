# Publishing Coactra to PyPI

Status as of 2026-06-05 — **pre-publish checklist**:

- Build the distribution and run `twine check` before publishing.
- Verify URLs, classifiers, the README, and the package name before publishing.
- Verify the capability/backend extras resolve and the wheel carries normal version deps.
- **Not yet on PyPI** — the name still needs to be claimed (this is the first publish).

## The distribution

Coactra ships as a single distribution; capabilities are selected via extras
(e.g. `pip install "coactra[memory,workflow]"`).

| Distribution | Version | Dir |
|---|---|---|
| coactra | 0.1.0 | `coactra/` |

For a first public release set the version as you like (`internal/RELEASE_POLICY.md`).

## Build + validate (reproducible, offline-safe)

```bash
rm -rf dist-all
(cd coactra && uv build --out-dir ../dist-all)
uvx twine check dist-all/*          # must say PASSED for both artifacts (1 sdist + 1 wheel)
```

## Option A — manual upload (recommended for the FIRST publish)

Simplest way to claim the names.

```bash
# 1. (optional) dry-run against TestPyPI first
uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-TESTTOKEN dist-all/*

# 2. real upload
uv publish --token pypi-XXXXXXXX dist-all/*
#   (equivalently: uvx twine upload dist-all/*)

# 3. verify in a clean env
python -m venv /tmp/v && /tmp/v/bin/pip install "coactra[agent]" && \
  /tmp/v/bin/python -c "import coactra.agent; print('ok')"
```

A first-upload token can be an **account-scoped** token (PyPI → Account settings → API tokens). After the project exists, replace it with a **per-project** token or switch to Option B.

## Option B — GitHub Actions trusted publishing (recommended for ongoing releases)

`.github/workflows/release.yml` (in this repo) builds the `coactra` distribution and uploads via OIDC — no stored tokens. Triggered by pushing a tag matching `v*`.

One-time PyPI setup for the `coactra` project: PyPI → the project → Settings → Publishing → add a *Trusted Publisher* (or a *pending publisher* before the project exists) with:
- Owner: `DataOpsFusion`
- Repository: **the actual repo slug** (`coatra` today — or `coactra` if you rename it first; see note below)
- Workflow: `release.yml`
- Environment: `pypi`

Then: `git tag v0.1.0 && git push origin v0.1.0`.

## ⚠️ Repo-name note (affects Option B)

The package metadata URLs say `DataOpsFusion/coactra`, but the **actual GitHub remote is `DataOpsFusion/coatra`** (the repo slug is misspelled relative to the project). Trusted publishing matches on the real `owner/repo`, so either:
- rename the GitHub repo `coatra → coactra` first (then everything is consistent), or
- configure the PyPI trusted publishers with repo `coatra` and leave it.

Manual upload (Option A) is unaffected by this.

## What you need to do (human-only)

1. Have a PyPI account; pick **Option A** (token, simplest) or **Option B** (trusted publishing).
2. Confirm the `coactra` name is free on PyPI. If it is taken, rename the distribution before publishing.
3. Decide the first-release version.
4. Merge the consolidation branch → `main` so the corrected metadata is what ships.
5. (Optional but recommended) dry-run to TestPyPI, then publish.
6. Tag the release after merge.

Run the build/check commands locally before publishing. Uploading to PyPI is irreversible for a version, so the final upload should be manual or a deliberate trusted-publishing release.
