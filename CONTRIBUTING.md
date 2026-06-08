# Contributing to Coactra

Coactra is an alpha-quality Python package. Its capability modules (`coactra.ai`,
`coactra.memory`, `coactra.workspace`, `coactra.workflow`, `coactra.team`,
`coactra.agent`) are designed to stay **thin orchestration layers over
best-of-breed libraries** — see [docs/concepts/library-map.md](docs/concepts/library-map.md) for the design
philosophy and [docs/maintainers/improvement-backlog.md](docs/maintainers/improvement-backlog.md)
for the current work list.

## Layout

A single `coactra` distribution lives under `coactra/`, with one `pyproject.toml`,
a `src/` tree with a lazy PEP 562 top-level `__init__.py` (heavy symbols like `Agent`,
`Workflow`, and `Team` are resolved on first attribute access to avoid pulling optional
dependencies at import time), and `tests/`.
`coactra.agent` is the only module that depends on the others; the capability
modules are independent and must not depend on each other except through their
optional `integrations/` modules.

## Install from source

Install the local checkout editable when developing the package:

```bash
python -m pip install -e './coactra[all,dev]'
```

## Tests

```bash
make test                     # default non-live suite
cd coactra && python -m pytest -q -m 'not live'
make live-check               # inventory live checks without running them
COACTRA_RUN_LIVE=1 make live-check
```

The dependency-light core is offline-friendly. Tests that need optional extras or
live services (Postgres, Neo4j, Keycloak, Temporal, Prefect) skip cleanly when the
dependency or environment is absent. Live tests are marked `live` and excluded
from the default pytest run; execute them through `make live-check` so the
release timeout and credential checks stay consistent.

Run type checking separately:

```bash
make type
```

`make type` requires Pyright from the development environment (`coactra[dev]`).
The combined `make release-check` target validates packaging and runtime release
gates, but type checking remains its own CI job.

## Branch workflow

Use `main` only for releasable code. PyPI publishing runs from `main`, so every
merge into `main` must be ready to be tagged. Versions are derived from `v*` git tags via `hatch-vcs`, not edited directly in `coactra/pyproject.toml`.

Use `dev` as the integration branch for work that is ready to combine but not yet
released. Create feature branches from `dev`, open pull requests back into `dev`,
and let CI pass before merging.

Recommended flow:

```bash
git checkout main
git pull origin main
git checkout -b dev
git push -u origin dev

git checkout dev
git pull origin dev
git checkout -b feature/my-change
# work, commit, push, then open PR: feature/my-change -> dev
```

When `dev` is ready to release, create a release branch from `dev`, update the
changelog, and open a pull request into `main`. After merge, create the release
tag that supplies the package version.

```bash
git checkout dev
git pull origin dev
git checkout -b release/0.1.1
# update CHANGELOG.md; version comes from the release tag
git push -u origin release/0.1.1
# open PR: release/0.1.1 -> main
```

Do not push a release tag that republishes the same version after `main` has
already published it; PyPI rejects duplicate uploads for an existing version.

## CI guardrails

`.github/workflows/ci.yml` installs `./coactra[all,dev,a2a,agent-gateway]` and
runs the default non-live test suite (`pytest -q -m 'not live'` from `coactra/`).
You can reproduce it locally with `make test`.

CI also runs a separate Pyright typecheck job. Reproduce it locally with
`make type` after installing the development extra.

`.github/workflows/docs.yml` builds the MkDocs site for pushes and pull requests
against `dev` and `main`. Only pushes to `main` deploy GitHub Pages.

## Public API and release discipline

Before exposing a new public symbol, walk the checklist in
[docs/maintainers/release-policy.md](docs/maintainers/release-policy.md) (preferred import
root, stability tier, API test, contract test for Protocols/adapters, no third-party
type leaks into the stable shell). Group changelog entries by the categories in that
policy and add them to [CHANGELOG.md](CHANGELOG.md).

## Style

- Python 3.12+, modern type hints.
- Ruff for lint + format.
- Function-first application code; classes only for durable state, backend
  boundaries, and long-lived facades.
