# Changelog

All notable changes to the Coactra library are documented here. Coactra is still
alpha software; entries describe the current unpublished working tree, not a
compatibility guarantee.

## [Unreleased]

### Added
- Root `Agent`, `Team`, `Workflow`, `Skill`, `RemotePeer`, `mcp`, `oidc`, and
  `serve_agent` public imports.
- Public `mcp(url, ...)` tag for additive remote MCP toolsets.
- Canonical `coactra.team` package with the Team facade implementation and lower-level `coactra.team.directory` internals.
- Canonical `coactra.workflow.ledger` package for durable work-order storage and adapters.
- Process-local fleet registry primitives for resolving named remote peers.
- Root Makefile targets for tests, lint, typing, examples, base-install smoke tests, clean wheel/sdist install validation, stale-path scanning, live backend inventory, and the combined `release-check`.

### Changed
- Agent runtime MCP toolset wiring is isolated behind `coactra.agent.toolsets`.
- Documentation and examples use `auth=` for gateway/static-token auth instead of
  the removed `token=` spelling.
- Release policy now reflects dynamic versions from git tags via `hatch-vcs`.
- The durable work-order implementation moved from `coactra.jobs.work` to `coactra.workflow.ledger`.
- Directory/org implementation moved from `coactra.directory` to `coactra.team.directory`.

### Removed
- Compatibility-only wrappers for old import paths: `coactra.agent.team`,
  `coactra.directory.store`, `coactra.directory.sqlite_store`,
  `coactra.workspace.integrations.organization`, and the full `coactra.jobs` / `coactra.directory` roots.
- Obsolete migration/handoff maintainer docs that described removed package shims.
