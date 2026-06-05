# Contributing to Coactra

Coactra is an alpha-quality Python package. Its capability modules (`coactra.ai`,
`coactra.memory`, `coactra.workspace`, `coactra.jobs`, `coactra.directory`,
`coactra.agent`) are designed to stay **thin orchestration layers over
best-of-breed libraries** — see [docs/LIBRARIES.md](docs/LIBRARIES.md) for the design
philosophy and [docs/internal/IMPROVEMENT_BACKLOG.md](docs/internal/IMPROVEMENT_BACKLOG.md)
for the current work list.

## Layout

A single `coactra` distribution lives under `coactra/`, with one `pyproject.toml`,
a `src/` tree (PEP 420 `coactra` namespace, no top-level `__init__.py`), and `tests/`.
`coactra.agent` is the only module that depends on the others; the capability
modules are independent and must not depend on each other except through their
optional `integrations/` modules.

## Install from source

The distribution is **not on PyPI yet** — install it editable from the repo:

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

## CI guardrails

`.github/workflows/ci.yml` installs `./coactra[all,dev]` and runs the test suite
(`pytest -q` from `coactra/`). You can reproduce it locally with `make test`.

## Public API and release discipline

Before exposing a new public symbol, walk the checklist in
[docs/internal/RELEASE_POLICY.md](docs/internal/RELEASE_POLICY.md) (preferred import
root, stability tier, API test, contract test for Protocols/adapters, no third-party
type leaks into the stable shell). Group changelog entries by the categories in that
policy and add them to [CHANGELOG.md](CHANGELOG.md).

## Style

- Python 3.12+, modern type hints.
- Ruff for lint + format.
- Function-first application code; classes only for durable state, backend
  boundaries, and long-lived facades.
