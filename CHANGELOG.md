# Changelog

All notable changes to the Coactra library suite are documented here. The format
follows the change categories defined in [docs/RELEASE_POLICY.md](docs/RELEASE_POLICY.md)
(Added / Changed / Deprecated / Removed / Fixed / Security / Adapter maturity /
Migration notes).

Packages are versioned independently (see the [versioning model][rp]); the umbrella
`coactra` distribution pins the compatible sibling ranges and acts as the published
compatibility table. This file groups changes across the suite per release; tag the
affected package(s) on each entry.

[rp]: docs/RELEASE_POLICY.md#versioning-model

## [Unreleased]

### Added
- `coactra.kernel` beta shell (`Kernel` / `Session` / `Task`) — a small typed
  facade around plain task functions.
- Machine-readable adapter manifest completed to full coverage
  (`docs/adapter_maturity.json`, 28 adapters) plus a CI parity check
  (`scripts/check_adapter_maturity.py`) that keeps it in sync with
  `docs/ADAPTER_MATURITY.md`.
- `CHANGELOG.md` and `CONTRIBUTING.md`.

### Fixed
- `docs/ADAPTER_MATURITY.md` referenced the in-process memory backend as
  `InProcessMemoryBackend`; the actual class is `InProcessBackend`.

### Changed
- Install docs now state plainly that the `coactra-*` distributions are not yet on
  PyPI and are installed from the monorepo today.
- README / Quickstart now signpost that the default `make_agent(...)` uses an
  in-process `FakeAI` echo model, and show how to wire a real model.

### Packaging
- Added `classifiers` to `coactra-orchestration` and the `coactra` umbrella, and a
  `[tool.hatch.build.targets.sdist]` block to `coactra-ai`, for parity with the
  other distributions.

### Adapter maturity
- No backend maturity changes. Stub adapters (Daytona, E2B, OpenHands, Neo4j org
  store, FastMCP server) remain named seams that raise on construction.

## Versioning snapshot

| Package | Version |
|---|---|
| coactra-ai | 0.2.0 |
| coactra-memory | 0.2.0 |
| coactra-organization | 0.2.0 |
| coactra-agent | 0.2.0 |
| coactra-workspace | 0.1.0 |
| coactra-orchestration | 0.1.0 |
| coactra (umbrella) | 0.1.0 |
