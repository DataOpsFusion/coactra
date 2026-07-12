# Scope Unification Design (as built)

**Status:** Implemented 2026-07-12. This is the design record for the change; the
implementation landed in the same-day commit that adds this file.

**Goal:** Exactly one public `Scope` class in the whole library, so identity, memory,
workspace, and workflow partitioning all speak the same vocabulary — the second
milestone of the AgentSpec consolidation direction (see
`docs/superpowers/plans/2026-07-12-agentspec-consolidation.md`).

## Decisions

1. **`coactra.scope.Scope` is the only scope.** Frozen dataclass:
   `tenant_id`, `namespace="default"`, `agent_id=None`, `session_id=None`.
   Core validation rejects `:`, `*`, and NUL in every component (the injectivity
   rule storage keys need). Its optional dimensions ARE the sharing model:
   - `agent_id` set → that agent's private memory/desk
   - `agent_id=None` → pool shared across the namespace
   - `session_id` set → narrowed to one conversation
   - different `namespace` → isolated partition within the same tenant
2. **Storage keys broke cleanly** (approved: no production data existed).
   Every engine key now encodes `tenant_id` and `namespace`; `agent_id` and
   `session_id` narrow when set. The old memory-package rule "namespace=None means
   private" is gone — sharing is expressed by which scope you pass.
3. **Workspace desks gained the namespace level:**
   `<base>/<tenant_id>/<namespace>/<agent_id>/`. Path safety
   (`is_safe_path_component`) is enforced at the workspace boundary on all three
   components; the core Scope stays permissive about `/` so memory namespaces like
   `"department/infrastructure"` keep working.
4. **The wiring gap closed.** `build_agent` passes the spec's full `Scope` through
   to runtime wiring (`bind_runtime_memory(memory, scope=...)`), so namespace and
   session flow into memory bindings. Previously only tenant+agent flowed — two
   agents with the same tenant and name in different namespaces shared memory.
   `Agent` now exposes a public `.scope` property.

## Deleted

- `coactra.memory.types.Scope` (pydantic, `tenant`/`agent`/`session` field names)
- `coactra.workspace.scope.Scope` (pydantic path key)
- `coactra.scope._TenantNamespaceScope` (shared pydantic base)
- Re-export shims: `agent/domain/scope.py`, `workflow/domain/scope.py`,
  `workflow/ledger/domain/scope.py`
- All five `Scope.to_*_kwargs()` converters
- `AuthorizedMemory`'s internal memory-Scope→core-Scope conversion

After this change, `grep -rn "class Scope" src` returns one hit.

## Rejected alternatives

- **Canonical-at-boundary only** (keep package scopes as private storage-key types):
  only wins if stored keys must be preserved; they didn't. Leaves two vocabularies.
- **Wiring fix only** (thread namespace/session, keep both scope classes): minimal
  churn but fails the one-vocabulary goal.

## Risks and how they resolved

- **Pydantic models embedding a stdlib dataclass** (ledger `scope: Scope` fields):
  pydantic v2 validates stdlib dataclasses natively; covered by
  `test_ledger_scope_round_trips_as_the_canonical_dataclass`.
- **Cross-namespace isolation regression:** covered by
  `test_memory_namespace_and_session_do_not_cross_scope` and the shared-pool test
  `test_memory_shared_pool_uses_agent_id_none` in `tests/agent/test_scope_wiring.py`.

## Verification (independent, post-implementation)

564 passed / 8 skipped / 1 xpassed; ruff clean; pyright 0 errors; single-Scope and
zero-leftover greps clean.
