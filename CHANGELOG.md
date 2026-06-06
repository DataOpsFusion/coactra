# Changelog

All notable changes to the Coactra library are documented here. The format
follows the change categories defined in
[docs/maintainers/release-policy.md](docs/maintainers/release-policy.md)
(Added / Changed / Deprecated / Removed / Fixed / Security / Migration notes).

Coactra ships as a single `coactra` distribution; capabilities are selected via
extras (e.g. `pip install "coactra[memory,workflow]"`). This file groups changes
per release.

## [Unreleased]

### Added
- `coactra.kernel` beta shell (`Kernel` / `Session` / `Task`) — a small typed
  facade around plain task functions.
- Single source of truth for `Scope` (`coactra.scope.Scope`) and `TenantRouter`
  (`coactra._routing`).
- `CHANGELOG.md` and `CONTRIBUTING.md`.

### Changed
- Consolidated the 7 distributions into one `coactra` package; capabilities are
  selected via extras (e.g. `pip install "coactra[memory,workflow]"`). Compat
  shims preserve the old `coactra.work`, `coactra.workflow`, `coactra.orchestration`,
  and `coactra.organization` import roots.
- Install docs now point users at the PyPI `coactra` distribution and keep editable
  source installs for contributor workflows.
- MkDocs-based documentation site with GitHub Pages deployment from `main`.
- Dedicated MkDocs example pages for runnable scripts and sample projects.
- PyPI release versions now come from `v*` Git tags via `hatch-vcs`, with the
  release workflow checking that the built wheel version matches the tag.
- README / Quickstart now signpost that the default `make_agent(...)` uses an
  in-process `FakeAI` echo model, and show how to wire a real model.

### Removed
- The adapter-maturity apparatus (`docs/ADAPTER_MATURITY.md`,
  `docs/adapter_maturity.json`, and the CI parity check) plus the unimplemented
  stub adapters (Daytona, E2B, OpenHands, Neo4j org store, FastMCP server).

## Versioning snapshot

| Package | Version |
|---|---|
| coactra | 0.1.0 |
