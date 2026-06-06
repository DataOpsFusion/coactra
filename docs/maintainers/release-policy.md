# Release Policy

This policy exists so Coactra can stay a long-lived thin library suite instead of an unstable collection of useful internals.

## Versioning Model

Coactra publishes **one distribution** (`coactra` on PyPI). Until v1, APIs may still change, but public changes should be intentional and documented. After v1, stable public APIs follow semantic versioning:

- patch: compatible fixes only
- minor: compatible additions and deprecations
- major: removals or breaking changes to stable APIs

Optional extras (`coactra[sql]`, `coactra[langgraph]`, …) version with the main package. Document extra requirements in release notes when a release adds or changes backend dependencies.

## Stability Tiers

| Tier | Meaning | Allowed changes |
|---|---|---|
| stable | preferred public API for application code | additive changes only within a major version; removals require deprecation window |
| beta | public but still settling | changes allowed with changelog and migration note |
| experimental | exploratory adapter, hook, or integration | may change or be removed; never required by stable examples |
| compatibility | old import path or alias | no new features; remove only after migration window |
| internal | implementation detail | can change without notice |

Symbol-level tiers and import paths are listed in [../API_INDEX.md](../API_INDEX.md).

## Stable Import Roots

Application docs and examples should prefer the V1 surface documented in [../API_INDEX.md](../API_INDEX.md):

- `coactra.scope` — `CoactraScope`
- `coactra.memory` — `Memory`, `make_backend`
- `coactra.jobs` — `WorkManager`, `WorkOrder`, `WorkScope`, `Orchestrator`, `Procedure`
- `coactra.workspace` — `open_workspace`, `Workspace`
- `coactra.agent` — `make_agent`, `Agent`, `Scope`, ports and collaboration policy
- `coactra.errors` — `CoactraError`, `ErrorCode`, `MissingExtraError`
- `coactra.ai` — `ask`, `structured`, `ReasoningEngine` (requires `coactra[ai]`)
- `coactra.directory` — `Organization`, `OrgStore`, `Authorizer` (requires `coactra[organization]`)

Beta roots (`coactra.kernel`, `coactra.plugins`) and experimental workflow symbols (`DurableLangGraphEngine`, `build_graph`, …) are public but not stable-tier. See the API index for the full list.

Compatibility shims (`coactra.orchestration`, `coactra.work`, `coactra.workflow`, `coactra.organization`) remain documented in [../concepts/naming-migration.md](../concepts/naming-migration.md); do not use them in new code.

## Deprecation Rules

1. Add the replacement path first.
2. Add tests for the replacement path.
3. Document the old path in a compatibility manifest.
4. Emit a warning where practical.
5. Keep the old path for at least one minor release after the warning.
6. Remove only in a major release or explicitly documented pre-v1 breaking release.

## Adapter Maturity Is Not API Stability

An adapter can be import-stable but operationally experimental. Track both dimensions:

- API stability: can the constructor/import contract change?
- adapter maturity: is the backend suitable for production?

Examples:

- `LocalFilesystemBackend` can be stable as a reference backend while local exec remains production-risky.
- `DurableLangGraphEngine` can be implemented while its restart contract still depends on host checkpointer configuration.
- Temporal and Prefect workflow adapters should not be marked production-ready until their resume semantics and integration tests are documented.

## Runtime Resume Semantics

Every workflow runtime adapter should declare one of:

| Value | Meaning |
|---|---|
| same-thread | `resume(thread_id, ...)` continues the same durable execution |
| new-run-with-prior-state | resume starts a new external run carrying previous state and decision |
| unsupported | adapter can start but cannot resume |
| host-owned | Coactra passes the request through; host workflow code owns real resume behavior |

This matters because LangGraph, Temporal, and Prefect do not expose identical durability shapes.

## Publishing

PyPI releases use **tag-based Trusted Publishing** via `.github/workflows/release.yml`:

```bash
git tag v0.2.0
git push origin v0.2.0
```

The pushed tag is the package version source of truth; `hatch-vcs` turns `v0.2.0` into `coactra==0.2.0`. Do not edit `coactra/pyproject.toml` for each release version.

Configure the PyPI Trusted Publisher for workflow `release.yml`, environment `pypi`, project `coactra`.

Do **not** publish on every merge to `main`. The legacy `workflow.yml` push trigger is disabled; it remains as a manual build-only workflow for smoke checks. See [../operations/publishing.md](../operations/publishing.md).

## Changelog Categories

Each release note should group changes as:

- Added
- Changed
- Deprecated
- Removed
- Fixed
- Security
- Adapter maturity
- Migration notes

## Public API Review Checklist

Before exposing a new public symbol:

1. Is it exported from the preferred package root?
2. Is it listed in `docs/API_INDEX.md`?
3. Does it have a stability tier?
4. Is there a public API test?
5. Is it covered by a contract test if it is a Protocol or adapter?
6. Does it leak a third-party provider type into the stable shell?
7. Does it need an optional extra marker?
8. Does it affect tenant isolation, state persistence, or secrets?

If the answer to 6 is yes, keep it beta or adapter-local until the leak is removed.
