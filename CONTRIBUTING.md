# Contributing to Coactra

Coactra is an alpha-quality, multi-package Python monorepo. The packages
(`lib-ai`, `memory`, `workspace`, `orchestration`, `organization`, `agent`, and the
`coactra` umbrella) are designed to stay **thin orchestration layers over
best-of-breed libraries** — see [docs/LIBRARIES.md](docs/LIBRARIES.md) for the design
philosophy and [docs/IMPROVEMENT_BACKLOG.md](docs/IMPROVEMENT_BACKLOG.md) for the
current work list.

## Layout

Each package is independently installable, with its own `pyproject.toml`, `src/`
tree (PEP 420 `coactra` namespace, no top-level `__init__.py`), and `tests/`.
`coactra-agent` is the only package that depends on the others; the four
capability packages are siblings and must not depend on each other except through
their optional `integrations/` modules.

## Install from source

The distributions are **not on PyPI yet** — install editable from the monorepo:

```bash
python -m pip install -e './coactra[dev]'
python -m pip install -e './memory[dev]'
python -m pip install -e './workspace[dev]'
python -m pip install -e './jobs[dev]'
python -m pip install -e './agent[dev]'
# dependency-complete lanes:
python -m pip install -e './lib-ai[dev]'
python -m pip install -e './directory[dev]'
```

## Tests

```bash
make test         # every package
make test-core    # the dependency-light core (coactra memory workspace orchestration agent)
cd <package> && python -m pytest -q   # a single package
```

The dependency-light core is offline-friendly. Tests that need optional extras or
live services (Postgres, Neo4j, Keycloak, Temporal, Prefect) skip cleanly when the
dependency or environment is absent.

## CI guardrails

`.github/workflows/ci.yml` runs `make test-core`, the `lib-ai` and `organization`
suites, and two inventory checks you can run locally:

```bash
python scripts/check_public_api.py        # public API inventory vs docs/API_INDEX.md
python scripts/check_adapter_maturity.py  # adapter manifest vs docs/ADAPTER_MATURITY.md
```

If you add or move an adapter, update **both** `docs/ADAPTER_MATURITY.md` and
`docs/adapter_maturity.json` (the parity check fails otherwise), and add/refresh its
file path so the manifest's existence check stays green.

## Public API and release discipline

Before exposing a new public symbol, walk the checklist in
[docs/RELEASE_POLICY.md](docs/RELEASE_POLICY.md) (preferred import root, stability
tier, API test, contract test for Protocols/adapters, no third-party type leaks into
the stable shell). Group changelog entries by the categories in that policy and add
them to [CHANGELOG.md](CHANGELOG.md).

## Style

- Python 3.12+, modern type hints.
- Ruff for lint + format.
- Function-first application code; classes only for durable state, backend
  boundaries, and long-lived facades.
