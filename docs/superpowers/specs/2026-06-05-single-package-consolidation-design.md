# Design: Collapse Coactra into one package with per-capability extras

- Date: 2026-06-05
- Status: Draft for review
- Scope: Repackage the seven Coactra distributions into a single `coactra` distribution whose capabilities are selected via optional extras; unify the duplicated cross-cutting primitives into a single source of truth. Repo: `/home/developer/mcp/library`, branch `main`.

## 1. Summary

Today Coactra ships seven independently-distributed packages (`coactra-ai`, `coactra-memory`, `coactra-workspace`, `coactra-jobs`, `coactra-directory`, `coactra-agent`, and the `coactra` umbrella installer) that, by rule, "depend on nothing." That rule forces every package to re-define shared primitives — most visibly **`Scope` (defined 6×)** and **tenant routing (implemented 6×)** — with a `CoactraScope` converter class existing solely to translate between the duplicate `Scope` types.

We will **collapse the seven distributions into one `coactra` distribution** whose capabilities are chosen with **optional extras** (`pip install "coactra[memory,workflow]"`). Because it is one package, the shared primitives are defined **once** (single source of truth, structurally enforced), while users still compose any subset of capabilities à la carte. Public import paths (`from coactra.memory import …`) are unchanged.

This is the first-party-only choice: Coactra offers capabilities its users mix and match. It is deliberately *not* the `coactra-core` + many-packages model (that's for a third-party adapter ecosystem / independent versioning), which we explicitly defer.

## 2. Motivation

- **Concrete overlap (evidence):** `Scope` defined in `agent/domain/scope.py`, `memory/types.py`, `orchestration/work/domain/scope.py`, `orchestration/workflow/domain/scope.py`, `workspace/scope.py`, plus `coactra/scope.py::CoactraScope` (the converter). Tenant routing: `TenantAgentRouter`, `TenantReasoningStoreRouter`, `TenantMemoryBackendRouter`, `TenantWorkspaceBackendRouter`, `TenantOrgStoreRouter` are bespoke, while `orchestration` already has a clean generic `TenantRouter[T]` the others didn't reuse.
- **Root cause:** "siblings depend on nothing" → no shared home → duplication is mandatory. The duplication is the *price of that rule*, not an accident.
- **Real requirement is mix-and-match *usage*, not separate distributions.** The user wants "use memory + organization without workspace," "you don't really need memory," etc. That is satisfied by **optional extras**, which work in a single package.
- **Timing:** nothing is on PyPI yet, so retiring the separate distribution names carries **zero deprecation cost**. This is the cheapest possible moment to consolidate.

## 3. Decision and alternatives considered

**Chosen: one `coactra` package + per-capability extras (Pattern B).**

| Alternative | Why not (now) |
|---|---|
| Keep 7 independent packages, no shared core (current) | The "unstable middle" — forces the Scope×6 / router×6 duplication. No mature suite does this. |
| `coactra-core` + 6 independent packages (Pattern A) | The right model only if we want a **third-party adapter ecosystem** or **independent versioning**. We don't, for now. More machinery than needed. |
| Vendoring/codegen of shared types | Copies are distinct Python types → breaks cross-capability interop; still "two files, one job." |

**Reversibility:** because the public import paths (`coactra.<capability>`) are a PEP 420 namespace and do not change, a future split back into `coactra-core` + separate packages is mostly a *packaging* change, not a rewrite. So "single package for now" is low-regret.

## 4. Target package layout

One distribution, `coactra`, `src/coactra/`:

```
src/coactra/
  scope.py          # THE Scope — single source of truth
  errors.py         # shared error types (CoactraError, ErrorCode, ...)
  _routing.py       # THE TenantRouter[T] generic (promoted from orchestration)
  ports.py          # base Port/Protocol marker(s)
  ai/               # capability submodules — internals unchanged
  memory/
  workspace/
  orchestration/    # contains jobs/ and workflow/ submodules
  organization/
  agent/            # contains agent/sdk/ (the just-landed elegant facade)
```

No `src/coactra/__init__.py` (preserve the PEP 420 namespace, as today). Tests consolidate under one `tests/` tree (or per-capability subdirs); one `README.md`; one `pyproject.toml`.

## 5. Extras scheme (granular — finer than the module layout)

Base install = `pydantic` only (all capability *code* importable; heavy backends gated):

```toml
[project.optional-dependencies]
ai            = ["litellm>=1.40", "instructor>=1.0", "numpy>=1.26"]
memory        = ["mem0ai>=0.1", "graphiti-core>=0.3"]
workspace     = ["daytona-sdk>=0.10", "e2b>=1.0"]
work          = ["sqlalchemy>=2.0"]
workflow      = ["langgraph>=1.0", "langgraph-checkpoint>=2.0", "cel-python>=0.5,<0.6", "Jinja2>=3.1"]
orchestration = ["coactra[work]", "coactra[workflow]"]   # convenience = both
organization  = ["sqlmodel", "openfga-sdk"]
agent         = ["pydantic-ai-slim>=1.0", "a2a-sdk>=1,<2"]
oauth         = ["httpx"]                                  # Keycloak token exchange
all           = ["coactra[ai,memory,workspace,orchestration,organization,agent,oauth]"]
# finer runtime adapters remain available, e.g.:
# orchestration-temporal = ["temporalio>=1,<2"], orchestration-prefect = ["prefect>=3"], ...
```

Examples that must work:
- `pip install "coactra[memory,organization]"` — memory + org, no workspace.
- `pip install "coactra[memory,workflow]"` — memory + procedure engine, no agent runtime.
- `pip install "coactra[agent,memory,workflow]"` — an agent that uses memory + workflow.
- `pip install "coactra[all]"`.

## 6. Single source of truth

### 6.1 Scope (the headline)
The per-capability `Scope` models differ in shape (e.g. `memory` uses `tenant`/`namespace`/`agent`; `agent`/`work` use `tenant_id`/`namespace`). `CoactraScope` already encodes the canonical superset + the conversion rules (`to_agent_kwargs`, `to_memory_kwargs`, `to_work_kwargs`, `to_workspace_kwargs`).

Plan: make the canonical `coactra.scope.Scope` the single model (superset fields: `tenant_id`, `namespace`, optional `agent_id`, `session_id`, with documented derivations). Each capability consumes `coactra.scope.Scope` directly; the five duplicate `Scope` classes are deleted. Where a capability needs a narrower view (e.g. memory's `group_id` key), it derives it via a method/property on the one `Scope`, not a separate type.

### 6.2 TenantRouter
Promote `orchestration`'s generic `TenantRouter[T]` to `coactra/_routing.py`. The five bespoke routers become thin `TenantRouter[...]` specializations (or are deleted in favor of direct use). Fold in the backlog's bounded-cache/eviction improvement (#23) once, here, so every capability benefits.

### 6.3 Errors / ports
Consolidate error types into `coactra/errors.py` and any base `Port`/`Protocol` marker into `coactra/ports.py`, imported by all capabilities.

## 7. Backward compatibility

- **Imports unchanged:** `from coactra.memory import …`, `from coactra.agent import …`, etc. all keep working (same namespace).
- **`CoactraScope` kept as a thin deprecation shim** (now an identity/adapter over the one `Scope`) for one release, so a mid-migration consumer doesn't break. Emits `DeprecationWarning`.
- **The one consumer change:** `homelab-mcp` replaces its six `coactra-*` path-source dependencies with a single `coactra` path/extras dependency. Its source imports do **not** change. We verify its test suite after the swap.
- **Versioning:** single version for the `coactra` distribution (start at `0.1.0`); the 0.1/0.2 skew and the compatibility-matrix concern disappear.

## 8. Migration plan (incremental, verify each step)

0. **Docs cleanup (subtractive, independent — do first, own commit):** delete the generated custom API inventory and its CI guard; keep the maintained docs and make `INTERFACES.md` the concise package-boundary guide. This only removes custom inventory work from the steps below; it touches no feature code.
1. **Skeleton:** create the one-package `pyproject.toml` (extras per §5) and move the seven `src/coactra/*` trees + tests into the single `coactra` package. Confirm the whole suite imports and `make test`-equivalent passes.
2. **Unify `Scope`:** introduce `coactra/scope.py::Scope` (canonical), repoint all capability imports, delete the five duplicates, convert `CoactraScope` to a deprecation shim. Run full suite.
3. **Unify `TenantRouter`:** promote the generic to `coactra/_routing.py`, replace the five bespoke routers, add bounded-cache eviction. Run router/conformance tests.
4. **Errors/ports:** consolidate into `coactra/errors.py` + `coactra/ports.py`; repoint imports.
5. **Consumer swap:** update `homelab-mcp` deps (6 → 1) and run its suite.
6. **Cleanup:** delete the now-empty per-package dirs/pyprojects; update `docs/` (LIBRARIES, INTERFACES, PUBLISHING, CHANGELOG, adapter manifest paths), the CI workflow (install one package with extras), and the build/`PUBLISHING.md` (one distribution).

## 9. Testing

- Offline-first; the existing per-capability suites move wholesale and must stay green at every step.
- CI guard `check_adapter_maturity.py` updated for the package paths and kept passing. The custom API inventory guard is removed; package-root API expectations stay covered by focused tests and docs.
- Build check: `uv build` produces one sdist + wheel; `twine check` passes.
- A focused test that a base install (`coactra` with no extras) imports every capability's pure-Python core, and that omitting an extra makes only that capability's heavy backend raise the existing `MissingExtraError`.

## 10. Risks

- **Scope reconciliation** is the only non-mechanical step (differing field shapes). Mitigation: the canonical model already exists as `CoactraScope`; adopt its fields, add per-capability derivation methods, lean on the existing suites to catch behavior drift.
- **The top-level shared module could itself bloat** (the langchain-core lesson, now internal). Mitigation: only proven-shared primitives live at the top (`scope`, `errors`, `_routing`, `ports`); capability-specific code stays in its submodule. Rule of three.
- **homelab-mcp breakage.** Mitigation: imports are unchanged; only its dependency declaration changes; verify its suite in step 5.

## 11. Non-goals / future

- `coactra-core` + multiple independently-published packages (Pattern A) — deferred until/unless a third-party adapter ecosystem or independent versioning is actually wanted. Reversible thanks to stable import paths.
- New capability *features* — this is a packaging + de-duplication refactor, not new behavior.
- Applying the "elegant facade" recipe to orchestration/workspace — separate, later effort (this consolidation makes it cleaner by giving those facades one Scope/router to build on).
