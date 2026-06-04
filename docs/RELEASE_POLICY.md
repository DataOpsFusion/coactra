# Release Policy

This policy exists so Coactra can stay a long-lived thin library suite instead of an unstable collection of useful internals.

## Versioning Model

Until v1, package APIs may still change, but public changes should be intentional and documented. After v1, stable public APIs follow semantic versioning:

- patch: compatible fixes only
- minor: compatible additions and deprecations
- major: removals or breaking changes to stable APIs

Packages may keep independent versions, but the repo should publish a compatibility table when a release expects specific sibling package ranges.

## Stability Tiers

| Tier | Meaning | Allowed changes |
|---|---|---|
| stable | preferred public API for application code | additive changes only within a major version; removals require deprecation window |
| beta | public but still settling | changes allowed with changelog and migration note |
| experimental | exploratory adapter, hook, or integration | may change or be removed; never required by stable examples |
| compatibility | old import path or alias | no new features; remove only after migration window |
| internal | implementation detail | can change without notice |

## Stable Import Roots

Application docs and examples should prefer:

- `coactra.scope`
- `coactra.kernel`
- `coactra.plugins`
- `coactra.errors`
- `coactra.ai`
- `coactra.memory`
- `coactra.workspace`
- `coactra.orchestration`
- `coactra.orchestration.work`
- `coactra.orchestration.workflow`
- `coactra.organization`
- `coactra.agent`
- `coactra.agent.integrations`

Compatibility imports such as `coactra.work` and `coactra.workflow` should remain documented as aliases, not preferred roots.

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
