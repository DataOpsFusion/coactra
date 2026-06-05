# Publishing Coactra to PyPI

Status as of 2026-06-04 — **publish-ready**:

- All 7 distributions build (sdist + wheel) and pass `twine check`. ✓
- Metadata correct: URLs → `github.com/DataOpsFusion/coactra`, classifiers, per-package READMEs. ✓
- Sibling extras resolve in-monorepo for dev (`[tool.uv.sources]`); published wheels carry normal version deps (e.g. `coactra-memory>=0.2`). ✓
- **Not yet on PyPI** — the names still need to be claimed (this is the first publish).

## The 7 distributions

| Distribution | Version | Dir |
|---|---|---|
| coactra-ai | 0.2.0 | `lib-ai/` |
| coactra-memory | 0.2.0 | `memory/` |
| coactra-organization | 0.2.0 | `organization/` |
| coactra-agent | 0.2.0 | `agent/` |
| coactra-workspace | 0.1.0 | `workspace/` |
| coactra-orchestration | 0.1.0 | `orchestration/` |
| coactra (umbrella) | 0.1.0 | `coactra/` |

Versions are independent by policy (`docs/RELEASE_POLICY.md`); the umbrella pins the compatible sibling ranges. For a first public release you may keep these as-is or set them all to one number — your call.

## Build + validate (reproducible, offline-safe)

```bash
rm -rf dist-all
for p in lib-ai memory workspace orchestration organization agent coactra; do
  (cd "$p" && uv build --out-dir ../dist-all)
done
uvx twine check dist-all/*          # must say PASSED for all 14 artifacts
```

Upload **order does not matter** — PyPI does not validate inter-package dependencies at upload time; install-time resolution works once all 7 are present.

## Option A — manual upload (recommended for the FIRST publish)

Simplest way to claim the names.

```bash
# 1. (optional) dry-run against TestPyPI first
uv publish --publish-url https://test.pypi.org/legacy/ --token pypi-TESTTOKEN dist-all/*

# 2. real upload
uv publish --token pypi-XXXXXXXX dist-all/*
#   (equivalently: uvx twine upload dist-all/*)

# 3. verify in a clean env
python -m venv /tmp/v && /tmp/v/bin/pip install coactra-agent && \
  /tmp/v/bin/python -c "import coactra.agent; print('ok')"
```

A first-upload token can be an **account-scoped** token (PyPI → Account settings → API tokens). After the projects exist, replace it with **per-project** tokens or switch to Option B.

## Option B — GitHub Actions trusted publishing (recommended for ongoing releases)

`.github/workflows/release.yml` (in this repo) builds all 7 and uploads via OIDC — no stored tokens. Triggered by pushing a tag matching `v*`.

One-time PyPI setup, **per project name** (7 of them): PyPI → each project → Settings → Publishing → add a *Trusted Publisher* (or a *pending publisher* before the project exists) with:
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
2. Confirm the 7 names are free on PyPI: `coactra`, `coactra-ai`, `coactra-memory`, `coactra-workspace`, `coactra-orchestration`, `coactra-organization`, `coactra-agent`. If any is taken, rename that distribution before publishing.
3. Decide first-release versioning (keep the mixed 0.1/0.2, or unify).
4. Merge `chore/packaging-docs-hygiene` → `main` so the corrected metadata is what ships.
5. (Optional but recommended) dry-run to TestPyPI, then publish.
6. Tag the release after merge.

Everything up to step 5 is automated/verified here; steps 1–6 require your PyPI account and the irreversible upload, so they're yours to run.
