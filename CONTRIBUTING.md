# Contributing to Coactra

Coactra is an alpha-quality Python package. Its capability modules (`coactra.ai`,
`coactra.memory`, `coactra.workspace`, `coactra.jobs`, `coactra.directory`,
`coactra.agent`) are designed to stay **thin orchestration layers over
best-of-breed libraries** — see [docs/concepts/library-map.md](docs/concepts/library-map.md) for the design
philosophy and [docs/maintainers/improvement-backlog.md](docs/maintainers/improvement-backlog.md)
for the current work list.

## Layout

A single `coactra` distribution lives under `coactra/`, with one `pyproject.toml`,
a `src/` tree (PEP 420 `coactra` namespace, no top-level `__init__.py`), and `tests/`.
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
make test                     # the full suite
cd coactra && python -m pytest -q
```

The dependency-light core is offline-friendly. Tests that need optional extras or
live services (Postgres, Neo4j, Keycloak, Temporal, Prefect) skip cleanly when the
dependency or environment is absent.

## Branch workflow

Use `main` only for releasable code. PyPI publishing runs from `main`, so every
merge into `main` must include the intended version in `coactra/pyproject.toml`.

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

When `dev` is ready to release, create a release branch from `dev`, bump the
version, update the changelog, and open a pull request into `main`. Merging that
PR to `main` triggers the PyPI publish workflow.

```bash
git checkout dev
git pull origin dev
git checkout -b release/0.1.1
# bump coactra/pyproject.toml and update CHANGELOG.md
git push -u origin release/0.1.1
# open PR: release/0.1.1 -> main
```

Do not push a release tag that republishes the same version after `main` has
already published it; PyPI rejects duplicate uploads for an existing version.

## CI guardrails

`.github/workflows/ci.yml` installs `./coactra[all,dev]` and runs the test suite
(`pytest -q` from `coactra/`). You can reproduce it locally with `make test`.

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
