# Coactra — Library Assessment Report

> External principal-architect review of `coactra` (single-package, ~15.5k LOC, 180 source files, 125 test files) on branch `codex/docs-system-mkdocs`. All current-state claims are sourced from **code**, not the maintainer docs (which, as Section 6 shows, have drifted out of date). Defect claims marked **[verified]** were executed against the installed package.

---

## 1. Executive Summary

Coactra is a **single-distribution, ports-and-adapters infrastructure library for multi-tenant AI agent systems**. It is not an agent framework; it is the durable substrate *underneath* one — scope/tenant isolation, a durable work-order ledger, backend-neutral memory, a workspace/desk abstraction, an org/authorization model, and a small agent-composition facade that wires AI/memory/workspace/workflow/org ports together. It deliberately wraps mature engines (LiteLLM, Instructor, LangGraph, Temporal, Prefect, mem0, Graphiti, OpenFGA) rather than reimplementing them.

The current design **matches that goal well**. This is one of the more architecturally disciplined alpha libraries I have reviewed: clean dependency direction, a real error contract, `py.typed` on every package, a published stability-tier index, secure-by-default boundaries, and zero `TODO/FIXME` in source. The maintainers have already done a serious internal audit.

The weaknesses are not in the architecture — they are in **surface discipline and doc/code truth**:

- **The single best concrete defect:** `API_INDEX.md` documents a compatibility-import migration path that does not exist. `from coactra.agent import FakeAI` raises `ImportError`, not the documented `DeprecationWarning`. **[verified]**
- **The maintainer docs have drifted** behind the consolidation. `improvement-backlog.md` and `roadmap.md` cite paths (`lib-ai/`, per-package `pyproject.toml`), a `.orig` file, and "problems" (stub adapters, optional A2A verifier) that the **code and CHANGELOG show are already removed or fixed**. The project's own audit no longer describes the project.
- **`Kernel` is marketed but unproven.** The README's headline "Quick Example" leads with `Kernel.builder()`, yet `Kernel` is beta, used by **zero** runnable examples, unreferenced anywhere in `src/`, and the roadmap itself says to *defer* it. The front door advertises an abstraction the codebase doesn't use.
- **`Scope` proliferation** is the main day-to-day API friction: every capability ships its own `Scope` with subtly different kwargs (`tenant_id`/`namespace` vs `tenant`/`namespace`/`agent`), so real apps alias `Scope` three ways.

Biggest architectural **risk**: not the code, but **maintenance surface vs. team size**. ~15.5k LOC spanning ~10 capability seams and a dozen optional backend adapters is a lot for a small team to keep honest — and the stale internal docs are the first visible symptom of that.

**Continue as one library or split?** Stay one distribution with extras. The consolidation was the right call; do not re-split.

**Ready for public users?** Ready for the **alpha / early-adopter** audience it honestly claims — not for broad "production-ready" adoption, and the README correctly says so.

```text
Overall assessment: Architecturally strong, self-aware alpha. Fix doc/code truth and
freeze the surface; the bones are good enough to reach v1 without a rewrite.

Public release readiness:  5/10  (broad public) — 7/10 for the alpha audience it targets
Architecture quality:      8/10
API clarity:               6/10
Maintainability:           6/10
Documentation:             6/10   (extensive, but drifted from code — see §6)
Testing:                   6/10
Security posture:          7/10
Developer experience:      6/10
```

---

## 2. Library Purpose and Identity

**What problem does it actually solve?** It gives builders of multi-tenant agent systems the *non-LLM* substrate: durable work orders with leases/retries/audit, tenant-scoped isolation at every boundary, swappable memory/workspace/workflow/org backends, and a composition facade — so application logic stays plain Python.

**Is the problem clear from code + docs?** Yes. README §"When to use / When not to use", `docs/concepts/library-map.md`, and `API_INDEX.md` make the identity unusually legible. A new dev can grasp the purpose in under 5 minutes from the README alone.

**Scope too broad / too narrow / too many things?** It is at the **upper edge of "broad but coherent."** Six capability domains (ai, memory, workspace, jobs[work+workflow], directory, agent) is a lot, but they share one spine (`Scope` + ports + errors) and the README frames them as opt-in extras. The one domain that feels **over-scoped for a thin orchestration layer** is `directory` — an AD-inspired OU tree with inheritance, blocking, per-member overrides, SQLite/Postgres/OpenFGA stores (`directory/__init__.py`, `directory/domain/organization.py:1-289`). That is a product in its own right, not a thin seam.

**One-sentence description it should adopt:**
> Coactra is the durable, multi-tenant substrate for AI agent fleets — scope isolation, work orders, memory, workspace, and policy — composed over the engines you already use.

**README tagline:**
> *Plain functions for behavior. Durable, tenant-scoped infrastructure for everything else.*

**What it should NOT try to do:** ship a tool-loop/agent runtime (PydanticAI/LangGraph own that), become a general workflow engine, or grow `directory` into a standalone IAM product.

**Positioning statement:**
> Coactra helps **platform engineers building multi-tenant agent systems** do **durable, isolated, auditable agent work** by providing **scope-bound work orders, memory, workspace, and policy ports**, without forcing them to **hand-roll tenancy, persistence, and backend wiring or marry one agent framework.**

---

## 3. Architecture Review

**Current architecture (as built):**
- One PEP 420 namespace package `coactra` (no top-level `__init__.py`), shipped as one wheel; capabilities are optional extras in `pyproject.toml`.
- Per-capability vertical slices, each with the same internal shape: `domain/` (pure types) → `ports`/Protocols → `backends`/`adapters` (integrations) → `routing.py` (per-tenant routers) → a facade (`make_agent`, `WorkManager`, `Memory`, `open_workspace`, `Organization`).
- A shared spine: `coactra.scope` (CoactraScope + `to_*_kwargs`), `coactra.errors` (one exception hierarchy + `ErrorCode`), `coactra._routing` (TenantRouter base).
- `agent/` is the only intended cross-capability composition layer (memory/workspace/workflow/org are wired *into* it, not into each other).
- Four naming-migration shims (`work`, `workflow`, `organization`, `orchestration`) re-export canonical roots and emit `DeprecationWarning`. **[verified working]**

**Main problems:**
- **Doc-layer leak into the public contract.** `API_INDEX.md`'s "deprecated root lookups" describe a `__getattr__` that exists for `directory`/`ai`/`memory` but **not** for `agent` — so the documented agent compat surface is fictional (§4, §6). **[verified]**
- **`Scope` is fragmented at the public boundary.** The shared `CoactraScope` exists, but each capability re-exports a *different* local `Scope`. Apps end up doing `Scope as AgentScope`, `Scope as MemoryScope`, etc. (see `examples/projects/ticket_triage/app.py:12-19`). The abstraction meant to unify (`CoactraScope.to_*_kwargs`) is not used by the examples it should anchor.
- **`directory` cohesion vs. the rest.** It carries both a "legacy directory write/read API (tenants/seats/members/reporting/escalation)" *and* the new OU-tree aggregate (`directory/__init__.py` docstring) — two models in one package, the largest root surface (~34 exports).
- **Speculative layer present:** `kernel.py` + `plugins.py` add a DI/hook shell used by nothing but its own tests (§19).

**Recommended architecture (keep the shape, tighten the seams):**
```
coactra/
  scope.py errors.py _routing.py        # spine — STABLE
  ai/  memory/  workspace/              # capability slices (domain→ports→backends→facade)
  jobs/{work,workflow}/
  directory/                            # consider: split legacy vs OU-tree, or pick one
  agent/                               # sole cross-capability composition root
  _internal/ (or *.adapters marked internal)
  # remove from front-door until proven: kernel.py, plugins.py
```
**Public:** the six facades + `CoactraScope` + `errors`. **Internal:** `*.adapters`, `*.backends`, `_optional`/`_stub`/`_errors`, `*.conformance`, `kernel`/`plugins` (demote to experimental).

The architecture **scales** as features grow *if* the boundary discipline in `improvement-backlog #8` becomes an enforced import-lint rather than a doc aspiration.

---

## 4. Public API Design Review

The API is **intuitive at the facade level** (`make_agent`, `WorkManager`, `Memory`, `open_workspace`) and well-tiered in `API_INDEX.md`. The problems are surface breadth and two concrete contract bugs.

| API | Current problem | Recommendation | Priority |
|---|---|---|---|
| `coactra.agent` compat lookups (`FakeAI`, `ToolTrie`, `build_a2a_app`) | **Documented as deprecated-but-reachable; actually `ImportError`/`AttributeError`** [verified] | Either add the `__getattr__` shim (like `ai`/`memory`) **or** delete the claim from `API_INDEX.md` §Compatibility | **P0** |
| `Scope` (×6 local variants) | Three different constructors; apps alias 3× | Make `CoactraScope` the documented default in every example; keep locals but de-emphasize | P1 |
| `Kernel`/`KernelBuilder`/`Session`/`Task` | Beta, unused in `src/` and examples, but headlined in README | MOVE to experimental; pull from README front door until an example needs it | P1 |
| `memory.Memory` + `Memory.sync` | Parallel async + `.sync` bridge; AI has neither | Keep the bridge pattern; document it as *the* sync story and mirror it in `ai` if async lands | P2 |
| `Orchestrator` vs `DurableOrchestrator` | Two facades, sync vs async, overlapping verbs | Document the choice explicitly; consider one facade with an explicit durable flag | P2 |
| `directory` (~34 exports, dual model) | Largest surface; legacy + OU-tree coexist | MERGE/RETIRE one model before v1 freeze | P1 |
| `agent.__version__ = "0.2.0"` | Hardcoded, contradicts dist `0.0.1.dev…` [verified] | DELETE per-subpackage `__version__`; single source via `importlib.metadata` | P2 |

**Can a user do something useful in 5 lines?** Yes — `examples/projects/ticket_triage/app.py` is clean. **Can they progressively learn?** Yes, the tiering supports it. **Does the API expose internals?** Mostly no, except the `Scope` fragmentation and the fictional agent-compat surface.

**Proposed clean V1 imports (already 90% there):**
```python
from coactra.scope import CoactraScope
from coactra.agent import make_agent
from coactra.jobs import WorkManager, WorkOrder
from coactra.memory import Memory, make_backend
from coactra.workspace import open_workspace
from coactra.errors import CoactraError, ErrorCode
# Kernel/Task/Session: from coactra.experimental import ... (until proven)
```
Why better: one `CoactraScope`, no `Kernel` at the front door, no fictional compat imports — every documented import actually resolves.

---

## 5. Developer Experience Review

**Strong:** offline-first examples (in-process fakes), plain-function application code, readable facades, `make test` one-liner, `py.typed` everywhere (real autocomplete).

**What would confuse / lose a first-timer:**
1. **The `FakeAI` silent echo.** `make_agent(scope=...)` with no `ai=` port returns a model that echoes the prompt (`draft == "completion:..."`). The README warns about this, but `examples/projects/ticket_triage/app.py:68` does **not** — a copy-paster sees plausible-looking output that is fake. Add a one-line inline comment in every example that calls `make_agent` without a real port.
2. **`Scope` aliasing.** Three imports of `Scope`, two kwarg spellings (`tenant_id` vs `tenant`). This is the #1 friction; lead with `CoactraScope`.
3. **README leads with `Kernel`** — an abstraction no example uses. New users will reach for it and find nothing downstream.

**Hello-World (the right first example):**
```python
from coactra.jobs import WorkManager, WorkOrder, WorkScope
work = WorkManager()
order = work.submit(WorkOrder(scope=WorkScope(tenant_id="acme", namespace="support"),
                              title="Triage latency"))
print(order.id, order.status)   # durable, scoped, audited — no LLM needed
```
**Real-world example:** the support-desk flow (agent draft + durable work + ticket memory) — already exists as `ticket_triage`; promote it.

**Minimal / Common / Advanced / Error / Plugin** examples: provide a 5-line work-order, the ticket flow, a SQL-backed `WorkManager` + real `AIPort`, a `try/except CoactraError` mapping `err.info.code`, and a custom `MemoryBackend` (§19). The first four exist in pieces; consolidate them under one "examples by journey" page.

---

## 6. Documentation Review

Documentation is **extensive and well-structured** (MkDocs site, concepts/getting-started/operations/maintainers split, an `API_INDEX.md` with tiers). The problem is **truth, not coverage.**

**Concrete drift findings (this is a headline finding, not a nitpick):**
- **`API_INDEX.md` §Compatibility is factually wrong** for the agent root: `FakeAI`/`ToolTrie`/`build_a2a_app`/`FakeMemory` are documented as reachable-with-`DeprecationWarning`; they raise `ImportError`/`AttributeError`. **[verified]**
- **`improvement-backlog.md` predates the consolidation.** It cites `lib-ai/`, `agent/src/coactra/...`, per-package `pyproject.toml` (all gone), a `directory/.../__init__.py.orig` (`find` returns nothing), and lists as live problems several things the **CHANGELOG marks Removed** (stub adapters Daytona/E2B/OpenHands/Neo4j/FastMCP and the adapter-maturity apparatus) or **Implemented** (#1 router options, #2 procedure router). Backlog #22 calls the A2A verifier optional/insecure; the **code is secure-by-default** (`a2a_server.py` raises `ValueError` without a verifier or explicit `allow_unauthenticated=True`).
- **Version story contradicts itself** across CHANGELOG (0.1.0), `agent.__version__` (0.2.0), and dist metadata (0.0.1.dev). **[verified]**

**Recommended doc structure** (you already have most of this — the gap is an accuracy pass + a generator):
```
docs/
  index.md  installation.md  getting-started/quickstart.md
  concepts/{library-map, interfaces, tenant-isolation, state-and-storage, security}.md  ✓ exist
  api-reference/   ← GENERATE API_INDEX from __all__ + a test that every documented import resolves
  examples/ (by journey)  guides/  operations/{production, publishing}.md  ✓
  maintainers/ (mark clearly "internal, may lag code")  changelog.md  ✓
```
**One mandatory test:** a `test_docs_imports.py` that imports every symbol named in `API_INDEX.md` and asserts it resolves (and that documented-deprecated ones actually warn). That single test would have caught the headline defect.

**README outline:** Tagline → Problem → Install (extras table) → 5-line work-order Hello-World (no LLM) → When to use / not use → Core concepts (Scope, ports, work orders) → Maturity → Links. **Drop `Kernel` from the lead example.**

---

## 7. Code Quality Review

**High-quality areas:**
- `errors.py` — exemplary: frozen `ErrorInfo`, `ErrorCode` StrEnum, `retryable` hint, `as_dict()` for transport, `coactra_error_from_exception` normalizer. Keep as-is.
- `scope.py` — small, validated, well-documented; `is_safe_path_component` is the single home for path-safety.
- `workspace/backends/local.py` — disciplined: traversal-confined `_resolve`, exec gated behind `allow_unsafe_exec`, `shell=False`, bounded output, timeout. A model adapter.
- Zero `TODO/FIXME/HACK/XXX` in source; consistent `from __future__ import annotations`; cohesive `WorkManager` lifecycle behind a single `_save_and_emit` choke point.

**Problem areas:**
- `jobs/workflow/backends/durable_langgraph.py` (**944 LOC**) — the one genuine complexity hotspot; holds thread→procedure mapping, scoped thread ids, snapshots, resume/restart, missing-procedure error paths. Highest-risk file in the repo.
- `directory/repository/sqlite_store.py` (510 LOC) and `jobs/work/service.py` (440 LOC, 21 public methods) — large but cohesive; `service.py` has 2–3 extractable collaborators (a `LeaseManager`, a budget enforcer, a stale-work reaper).
- Stale `agent.__version__` hardcode.

**Refactor first:** `durable_langgraph.py` (extract resume/restart into a tested sub-component before adding adapters). **Split candidate:** `jobs/work/service.py` (lease + budget + reap). **Merge/retire:** `directory` dual model. **Delete-or-demote:** `kernel.py`/`plugins.py` from the public front door. **No files need deletion** — the `.orig` the backlog worries about is already gone.

---

## 8. Error Handling Review

**This is a strength.** The hierarchy in `errors.py` is already close to the textbook recommendation:

```
CoactraError(code, retryable, details, cause)         # base, carries ErrorInfo + as_dict()
├─ ConfigError → MissingExtraError(extra, install hint)
├─ ValidationError            (ErrorCode.VALIDATION)
├─ AdapterError               (ErrorCode.PROVIDER)
├─ ExecutionError → TimeoutError(retryable=True)
├─ PermissionDeniedError      (ErrorCode.PERMISSION)
└─ SecurityError              (ErrorCode.SECURITY)
```

- Custom exceptions used correctly; machine-readable `ErrorCode`; `retryable` distinguishes transient from fatal; `MissingExtraError` gives an actionable `pip install coactra[extra]` hint — excellent DX for optional backends.
- `coactra_error_from_exception` normalizes arbitrary exceptions at boundaries and preserves `__cause__`.

**Gaps to close before v1:**
- Capability packages define their own local error classes (`AgentError`, `WorkspaceError`, `directory/errors.py`, `memory/backends/_errors.py`). Confirm each subclasses `CoactraError` so `except CoactraError` is a real catch-all — and add a contract test asserting it.
- Errors are not silently swallowed in the sampled code, but make this an explicit invariant (lint: no bare `except: pass`).

---

## 9. Type Safety and Data Model Review

**Good posture:** `requires-python >=3.12`, `py.typed` in all 7 package roots, Protocols for every port (`AIPort`, `MemoryPort`, `WorkPort`, …), frozen dataclasses (`ErrorInfo`, `CoactraScope`) and Pydantic v2 (`_TenantNamespaceScope`) where validation matters. Pydantic-2-only is the right single validation choice for a runtime-validated, multi-backend library — don't add attrs/dataclasses-validation on top.

**Issues:**
- **Type-checking coverage is narrow.** `pyright` `include` is only `errors.py`, `scope.py`, `workspace/`, `a2a_server.py`, and **excludes `**/integrations/**`** with `reportMissingImports = "none"` (`pyproject.toml:137-148`). So CI's green typecheck covers a small slice. Widen `include` incrementally toward the facades.
- **Ruff selects only `["F"]`** (pyflakes) — no bugbear (`B`), no security (`S`), no import-order. Add `B`, `S`, `I`, `UP` before v1.
- Mixed `Scope` types weaken the "one obvious type" story (§4).

Result objects (`WorkOrder`, `ExecResult`, `Recollection`) and errors are typed and stable enough to expose. Plugin/port interfaces are typed via Protocols — good for structural extensibility.

---

## 10. Testing Review

**Present:** 125 test files; 4 reusable conformance suites (`agent`, `memory`, `jobs/work`, `jobs/workflow`); base-install smoke test; CI matrix on 3.12/3.13 with `[all,dev,a2a]`; lint + pyright + wheel/twine gates. This is well above typical alpha hygiene.

**Weaknesses:**
- **Optional-extra coverage is gated/skipped** (27 skip/`importorskip` sites). Real adapters (LangGraph durable, Temporal, Prefect, mem0, Graphiti, OpenFGA, Postgres) may not exercise under the default lane → adapter drift is the likely first production failure.
- **Conformance gaps:** no reusable suite yet for `WorkspaceBackend`, `OrgStore`, `WorkflowEngine`, or the **tenant routers** (which the backlog already showed can silently drop methods/options).
- Tests lean toward behavior (good), but durable restart/resume is under-tested for the 944-LOC engine.

**Recommended structure** (align to existing `tests/<pkg>/`):
```
tests/<pkg>/{unit, contract(conformance), integration(extra-gated)}/  + regression/  + security/
```

**Top 20 tests to add first (specific):**
1. `test_docs_imports`: every `API_INDEX.md` symbol resolves; documented-deprecated ones emit `DeprecationWarning` (would catch the §1 defect).
2. Agent-root compat: assert the *intended* behavior (either import works+warns, or the doc is removed).
3. `CoactraError` catch-all: every package error subclasses `CoactraError`.
4. `TenantWorkspaceBackendRouter` forwards `ExecOptions` (regression).
5. `TenantProcedureStoreRouter` satisfies full `ProcedureStore` (exists/replace/delete).
6. Router conformance (generic): every protocol method forwards scope+options — parametrized over all 6 routers.
7. `WorkspaceBackend` conformance suite run against `LocalFilesystemBackend` **and** an in-memory fake.
8. Path traversal: `../`, absolute paths, and **symlink-escape** rejected by `_resolve`.
9. Workspace exec disabled by default; `allow_unsafe_exec=True` honors `timeout`/`max_output_bytes`/`cwd`/`env`.
10. A2A: `make_a2a_executor()` without verifier raises; `allow_unauthenticated=True` path is explicitly tested and (proposed) logs a warning.
11. Work lifecycle invariants: terminal-state guards reject illegal transitions.
12. Lease expiry + `reap_stale` reclaims and re-leases.
13. Idempotency: duplicate `idempotency_key` returns the same order.
14. Durable approval survives a simulated engine restart (or test documents it as host-owned).
15. Durable LangGraph resume with missing procedure raises the documented error.
16. Cross-tenant denial: memory/workspace/collaboration reject foreign-tenant scope.
17. Memory `_SyncBridge` parity with async API for `remember/recall/export`.
18. `MissingExtraError` raised (with install hint) when a backend's extra is absent.
19. `OrgStore` conformance across SQLite/Postgres/OpenFGA (mocked) for save/load round-trip.
20. Version single-source: `coactra.agent.__version__ == importlib.metadata.version("coactra")` (or remove the attribute).

---

## 11. Security Review

**Overall posture is good** — no dangerous patterns found (`grep`: no `pickle`, no `yaml.load`/`unsafe_load`, no `shell=True`, no `eval`/`exec`, no `verify=False`, no token logging). Findings are about *boundaries to document/harden*, not active holes.

**Finding A — A2A silent-insecure mode**
- Risk: low-moderate. Where: `agent/adapters/a2a_server.py`. The default is secure (missing verifier → `ValueError`), **[verified design]** but `allow_unauthenticated=True, verifier=None` proceeds with `claims={}` and **no warning**.
- Exploit: an operator flips the flag for local dev and ships it; unauthenticated callers reach the handler silently.
- Fix: log a `warning` at build and/or request time in insecure mode; add `build_production_a2a_app` that requires a verifier + allowed subject prefixes. Priority: **P1**.

**Finding B — Token cache lifecycle**
- Risk: low. Where: `agent/identity.py` `CachedAsyncTokenExchanger`. TTL cache, no max size, no invalidation/revocation.
- Why it matters: long-running multi-tenant services need bounded memory + logout/revocation.
- Fix: optional max size (LRU), `invalidate()`, metrics hook; document it as a convenience cache, not an authz source of truth. Priority: **P2**.

**Finding C — Workspace exec is not a jail (by design, well-labeled)**
- Risk: contained. Where: `workspace/backends/local.py`. Honest docstring; gated behind `allow_unsafe_exec`; `shell=False`; argv-only; bounded output/timeout. Symlink-escape appears caught by `_resolve` but is **untested** (see test #8).
- Fix: add the symlink-escape test; keep the "use a sandbox backend for untrusted tenants" guidance prominent. Priority: **P2**.

**Finding D — Tenant routers have no eviction/close**
- Risk: low (resource, not confidentiality). Where: all 6 `*routing.py`. One backend per tenant, cached forever.
- Fix: optional LRU/TTL + `close()` hooks. Priority: **P2**.

**Add `docs/concepts/security.md` content** (the file exists — populate it): rules for bearer tokens, what may/may not be persisted to memory/workspace, A2A header handling, Keycloak config, local exec, and a one-line `SECURITY.md` with a disclosure contact. Add `pip-audit`/Dependabot to CI (none present).

---

## 12. Performance Review

No benchmarks exist and **none should be invented**. Concrete hot paths actually found:

- **`memory._SyncBridge` calls `asyncio.run()` per call** — fine for scripts, a real cost in a sync server loop (event-loop spin-up per `remember/recall`). Measure; document as "prefer the async API in servers."
- **Unbounded per-tenant router caches** (§11-D) — memory growth in high-tenant-count deployments. Benchmark steady-state RSS vs. tenant count.
- **`durable_langgraph.py` (944 LOC)** — checkpoint/resume is the latency-sensitive durable path; benchmark start/resume round-trips against a real checkpointer.
- **Heavy optional imports** (litellm, langgraph, sqlmodel) are correctly behind extras and lazy `__getattr__` — keep base import light; add a test asserting `import coactra` pulls in none of them.

**Do NOT optimize yet:** `WorkManager` event emission, SQLite store, in-memory fakes — correctness-first, low traffic. **Benchmark before v1:** thin-layer overhead per work-order transition (the README's "thin" claim should have a number), sync-bridge cost, router memory.

---

## 13. Dependency Review

Core is **excellently minimal: `pydantic>=2.7` only.** Everything else is an opt-in extra. That is exactly right for a substrate library.

| Dependency | Role | Classification |
|---|---|---|
| `pydantic>=2.7` | core validation | **KEEP** (sole core dep — good) |
| `litellm`, `instructor` (`[ai]`) | provider routing + structured output | **KEEP / wrap** — do not reimplement |
| `langgraph` (`[langgraph]`) | default durable workflow | **KEEP** as adapter |
| `temporalio`, `prefect`, `dbos`, `dapr` | alt workflow runtimes | **OPTIONAL** — keep gated; ensure each has fake-client tests |
| `sqlmodel`/`sqlalchemy` (`[organization]`/`[sql]`) | org + work persistence | **KEEP**, optional |
| `mem0ai`, `graphiti-core` (`[mem0]`/`[graphiti]`) | memory backends | **KEEP**, optional |
| `openfga_sdk` | authz backend | **KEEP**, optional |
| `a2a-sdk`, `authlib`, `httpx` | agent transport/identity | **KEEP**, optional |
| `numpy` (in `[ai]`) | embeddings math | **OPTIONAL** — confirm it's truly required by `[ai]` or split out |

Groups are already well-formed (`core / dev / capability extras / backend extras / integrations / all`). One nit: the `integrations` and `all` extras duplicate long pinned lists by hand — derive them or test that they stay in sync. No dependency locks the *core* into one ecosystem — the key property for a thin layer. **Add a dependency CVE gate** (`pip-audit`) — currently absent.

---

## 14. Existing Library Comparison

Coactra is **not** reinventing the engines — it explicitly wraps them. The honest question is whether the *substrate* (scope + work ledger + ports) is differentiated. It is.

| Library | Solves | Use it? | Replace / Integrate / Learn |
|---|---|---|---|
| LangGraph / LangChain | graph execution, checkpointing | yes | **Integrate** (default `WorkflowEngine`) — already done |
| Temporal / Restate / Inngest / DBOS | durable execution, retries, signals | yes | **Integrate** as adapters; let them own durability, keep `WorkOrder` as the business ledger |
| LiteLLM + Instructor | provider routing + typed output | yes | **Integrate** behind `coactra.ai` — already done; don't grow it |
| CrewAI / AutoGen / PydanticAI | agent tool-loops, multi-agent | partial | **Learn from** (typed deps/tools) — do **not** rebuild the loop |
| mem0 / Zep / Graphiti | agent memory | yes | **Integrate** as `MemoryBackend` — already done |
| OpenFGA / SpiceDB | relationship authz | yes | **Integrate**; reconsider building the bespoke OU-tree in `directory` on top |
| Temporal/Celery work ledgers | job state | — | **Learn from**; Coactra's tenant-scoped `WorkOrder` with approvals/artifacts/audit is the genuine differentiator |

**Am I reinventing the wheel?** Mostly **no** — and where there's risk it's `directory` (a hand-rolled AD-style org/permission model that overlaps OpenFGA) and `kernel`/`plugins` (a DI/hook shell that PydanticAI/pluggy already do). **What justifies Coactra existing:** the combination of *first-class tenant Scope at every boundary* + *a durable, auditable WorkOrder ledger* + *backend-neutral ports* is not offered as a cohesive substrate by any single library above. That is the moat — lean into it; trim `directory` and `kernel` which are the parts most duplicative of mature tools.

---

## 15. API Stability and Versioning

The tiering work (`API_INDEX.md`, `release-policy.md`, roadmap) is genuinely ahead of most alphas. Gaps are enforcement and truth.

- **Stable:** `CoactraScope`, `make_agent`, `WorkManager`/`WorkOrder`, `Memory`/`make_backend`, `open_workspace`, `errors.*`, port Protocols.
- **Beta:** `Orchestrator`/`DurableOrchestrator`, `agent.integrations`.
- **Experimental:** `kernel`, `plugins`, `jobs.workflow` DSL, `DurableLangGraphEngine`, Temporal/Prefect/DBOS adapters, `*.adapters`/`*.backends`. **Move `kernel`/`plugins` here from "beta" and out of the README.**
- **Compatibility:** `coactra.{work,workflow,organization,orchestration}` shims (work + warn — verified). **The documented `coactra.agent` compat lookups are NOT real — fix or delete.**
- **Remove/settle before v1:** the `directory` dual model; per-subpackage `__version__`; the stale `improvement-backlog`/`roadmap` paths.

**Breaking changes to make NOW (before users depend on them):** unify on `CoactraScope` in docs/examples; demote `Kernel`; pick one `directory` model; delete `agent.__version__`. **Use SemVer** with `DeprecationWarning` windows (the shim machinery already proves you can). **Compatibility guarantee:** stable roots don't break without a deprecation window + changelog entry + migration note — and a `test_docs_imports` to keep the promise honest.

---

## 16. Packaging and Release Readiness

**Strong:** hatchling + `hatch-vcs` (version from `v*` git tags), PEP 420 namespace preserved intentionally, `py.typed` shipped, MIT license, sensible classifiers, `[project.urls]`, sdist includes README/tests, CI builds the wheel and runs `twine check`, release workflow asserts wheel-version == tag.

**Fix before publishing:**
- **Three-way version drift** [verified]: dist `0.0.1.dev68+g…`, `agent.__version__ = "0.2.0"`, CHANGELOG `0.1.0`. Delete per-subpackage `__version__`; expose one `coactra.__version__` via `importlib.metadata`. **P1 for release.**
- **No `v*` tag exists yet** → `hatch-vcs` falls back to `0.0.1.devN`. Cut a real `v0.1.0` tag before the first PyPI push.
- Confirm `dist/` and `dist-all/` are git-ignored (they appear in the tree).
- `ruff`/`pyright` coverage is narrow (§9) — widen before claiming type-complete.

**Release checklist:**
1. Pick `directory`/`Kernel`/`Scope` final shape (breaking changes now).
2. Fix `API_INDEX` compat claim + add `test_docs_imports`.
3. Single-source version; delete `agent.__version__`.
4. Tag `v0.1.0`; verify wheel version matches.
5. `pip-audit` + Dependabot in CI.
6. `twine check` (already wired) + test-PyPI dry run.
7. CHANGELOG `Unreleased` → `0.1.0`; verify "Removed" matches code.
8. README: drop `Kernel` lead; lead with the no-LLM work-order example.

---

## 17. Configuration Review

Config is **constructor-injection / factory-based** (`make_agent(...)`, `make_backend(...)`, `make_org_store(...)`, backend constructors like `LocalFilesystemBackend(base_dir, allow_unsafe_exec=...)`). There is **no global config object and no implicit env-var reading** in the sampled core — which is the right default for a library (explicit > ambient; no hidden global state).

**Strengths:** defaults are safe (exec disabled, fakes are obviously fake, scopes validated at construction). **One clear way** per capability via its `make_*` factory.

**Gaps:** there's no documented, typed way to configure timeouts/retries/log-level uniformly across capabilities; each surfaces its own knobs. For v1, consider a small optional typed `CoactraConfig` passed into factories (timeouts, retries, log level, cache bounds) — but **keep it optional**; do not introduce ambient global config.

```python
from coactra.config import CoactraConfig          # proposed, optional
cfg = CoactraConfig(default_timeout_s=30, max_tenant_cache=512, log_level="INFO")
agent = make_agent(scope=scope, config=cfg)
```
Secrets: never read implicitly; require explicit injection (tokens, DSNs) and document in `security.md`.

---

## 18. Logging, Observability, and Debugging

This is the **least-evidenced area** and the most likely real gap: the security grep found **no logging of secrets**, but also little structured logging in core. `otel` is an optional extra and `structlog` is only in the `integrations` bundle — so observability is opt-in/peripheral, not a first-class seam.

**Recommendation (keep it optional, make it real):**
- A single internal `coactra.logging` helper returning a namespaced logger per capability; library code uses it, never configures handlers (library logging etiquette — `NullHandler` by default).
- **Structured context on every log/event:** `scope.key`, work-order id, error `code`/`retryable`. `CoactraScope.as_event_metadata()` and `ErrorInfo.as_dict()` already give you the fields — wire them in.
- Expose the existing work **event stream** (`work.events(...)`) as the primary debugging surface; document it.
- Add the A2A insecure-mode warning (§11-A). Keep OTel tracing behind `[otel]`.
- **Logging policy:** WARNING for insecure/degraded modes, INFO for lifecycle transitions, DEBUG for adapter calls, **never** log token/secret values; correlation via `scope.key` + work id.

---

## 19. Extensibility and Plugin System

There are **two distinct extension mechanisms**, and they should be treated very differently:

**(a) Ports/adapters — the real, working extension system. KEEP.** Every capability is extended by implementing a typed Protocol (`MemoryBackend`, `WorkspaceBackend`, `WorkflowEngine`, `OrgStore`, agent ports) and passing it to a `make_*` factory. Conformance suites exist for four of them. A user can write a backend in well under 20 lines:

```python
from coactra.memory import MemoryBackend, Recollection, Scope

class EchoMemory:                       # structural — no base class needed
    async def remember(self, items, *, scope: Scope) -> None: ...
    async def recall(self, query, *, scope: Scope, k: int = 5) -> list[Recollection]:
        return [Recollection(text=f"echo:{query}")]

memory = Memory(backend=EchoMemory())   # done
```
Lifecycle: construct → inject → facade calls Protocol methods. Validation: conformance suite. Errors: raise `CoactraError` subclasses. **This is the system to advertise.**

**(b) `coactra.plugins` hook system — speculative. DEMOTE.** `PluginManager` + `on_task_start/end/error` hooks are used only by `Kernel`, which is used only by its own tests — zero `src/` consumers, zero examples. The roadmap itself says to defer plugins until hooks are real. Mark experimental, keep out of the public tier table, and don't let it become a second hidden orchestration framework.

**Action:** finish conformance suites for `WorkspaceBackend`, `OrgStore`, `WorkflowEngine`, and the tenant routers (§10). That closes the one real risk of the port system: silent adapter/router drift.

---

## 20. Maintainability Review

**Maintainability score: 6/10.**

**For:** clean dependency direction, one error contract, typed ports, conformance suites, zero TODOs, secure-by-default boundaries, an honest maturity statement. A new contributor can find their way via the consistent per-capability shape.

**Against (what hurts a small team over time):**
- **Surface vs. team size.** ~15.5k LOC, ~10 capability seams, ~15 optional backend adapters. Every adapter is a maintenance contract against a moving upstream (langgraph, temporal, mem0, openfga). The optional-extra CI lane (§10) is the only thing that will catch drift, and it's incomplete.
- **Doc/code drift is already visible** (§6) — the clearest early symptom of surface outpacing maintenance. The internal audit no longer matches the code.
- **`durable_langgraph.py` (944 LOC)** is a single-maintainer cognitive load.
- **`Scope` ×6 + dual `directory` model + speculative `kernel`** are three concept-duplications that each cost ongoing explanation.

**What becomes painful — and when:**
- *6 months:* the stale maintainer docs mislead a new contributor; `durable_langgraph` resume edge-cases.
- *10 users:* the fictional `agent` compat imports and `Scope` aliasing generate the same support questions repeatedly.
- *100 users:* unbounded tenant-router caches; adapter drift in an extra with no CI lane; pressure to stabilize `directory`/`kernel` you haven't frozen.
- *adding integrations:* without an enforced boundary lint (backlog #8) and per-adapter conformance, each new backend risks silent router/port drift.

**Simplify immediately:** unify `Scope` in docs; demote `kernel`/`plugins`; pick one `directory` model; regenerate `API_INDEX` from code with a verifying test; mark maintainer docs as "may lag code" and refresh them.

---

## 21. Roadmap Recommendation

You already have `docs/maintainers/roadmap.md` (v0.1→v1.0). It is sound in spirit; the critique is that it (a) under-weights the **doc/code truth** problem now blocking trust and (b) keeps `Kernel` on the table too long. Refine it; don't replace it.

**Phase 0 — Stop the bleeding (truth + freeze)**
- Goal: every documented import resolves; no fictional compat surface; one version number.
- Tasks: fix `API_INDEX` agent-compat claim (or add the `__getattr__`); add `test_docs_imports`; delete `agent.__version__`; refresh/flag `improvement-backlog` + `roadmap` as code-lagging; drop `Kernel` from README.
- Difficulty: Low. Risk: Low. Done when: `test_docs_imports` is green and CHANGELOG/version/dist agree.

**Phase 1 — Public API cleanup**
- Goal: one obvious way per concept. Tasks: `CoactraScope` as the documented default everywhere; demote `kernel`/`plugins` to experimental; decide `directory` single model. Difficulty: Medium. Risk: Medium (breaking — do it now). Done: examples use only stable roots + `CoactraScope`.

**Phase 2 — Docs & examples by journey**
- Goal: copy-safe examples. Tasks: no-LLM Hello-World; `FakeAI` inline warnings; "production replacements" block per example; populate `security.md`/`state-and-storage.md`. Difficulty: Low. Done: each example states local-vs-production backends.

**Phase 3 — Testing & CI**
- Goal: adapters can't drift unnoticed. Tasks: conformance for `WorkspaceBackend`/`OrgStore`/`WorkflowEngine`/routers; optional-extra CI lanes; widen ruff(`B,S,I`)/pyright include. Difficulty: High. Done: top-20 (§10) added; extra lanes green.

**Phase 4 — Security & reliability**
- Goal: no silent-insecure paths. Tasks: A2A insecure-mode warning + `build_production_a2a_app`; token-cache bounds/invalidirology; router eviction/`close`; `pip-audit`/Dependabot; symlink-escape test. Difficulty: Medium. Done: §11 findings closed.

**Phase 5 — Release prep**
- Goal: clean `v0.1.0`. Tasks: tag, verify wheel==tag, finalize CHANGELOG, test-PyPI dry run. Difficulty: Low. Done: installable from PyPI; `import coactra` pulls zero heavy deps.

---

## 22. Refactoring Plan

| Priority | Area | Problem | Fix | Risk |
|---|---|---|---|---|
| **P0** | `API_INDEX` + `agent/__init__` | Documented compat imports `ImportError` [verified] | Add `__getattr__` shim *or* delete the claim; add `test_docs_imports` | Low |
| **P1** | `Scope` (×6) | 3-way aliasing friction | Lead with `CoactraScope` + `to_*_kwargs` in all docs/examples; keep locals secondary | Medium (doc/example churn) |
| **P1** | `kernel`/`plugins` | Beta+headlined but unused | Demote to experimental; remove from README front door | Low |
| **P1** | `directory` | Dual model (legacy + OU-tree), largest surface | Pick one; mark the other compat/internal | Medium |
| **P1** | versioning | dist/agent/CHANGELOG disagree [verified] | Single-source via `importlib.metadata`; delete `agent.__version__` | Low |
| **P1** | maintainer docs | `improvement-backlog`/`roadmap` predate consolidation | Refresh; add "internal, may lag code" banner | Low |
| **P2** | `jobs/work/service.py` | 21 methods, 3 concerns | Extract `LeaseManager`/budget/reaper collaborators | Medium |
| **P2** | `durable_langgraph.py` | 944 LOC hotspot | Extract + test resume/restart sub-component before new adapters | Medium |
| **P2** | A2A insecure mode | silent `claims={}` | Warn on insecure mode; add `build_production_a2a_app` | Low |
| **P2** | tenant routers | unbounded cache | optional LRU/TTL + `close()` | Low |
| **P3** | `integrations`/`all` extras | hand-duplicated pin lists | derive or sync-test | Low |

**Refactor first:** P0 (it's a half-day and restores doc trust). **Do not touch yet:** the port/adapter shape, `errors.py`, `scope.py` validation, `workspace/local.py` — these are right. **Delete:** nothing (the `.orig` is already gone). **Hide behind internal:** `*.adapters`/`*.backends`/`*.conformance`, `kernel`/`plugins`. **Promote to stable:** the six facades + `CoactraScope` + `errors`.

---

## 23. Final Verdict

**Continue the library? Yes.** The core thesis — a tenant-scoped, durable, backend-neutral substrate for agent fleets, composed over mature engines — is sound, differentiated, and unusually well-executed for an alpha. Do not rewrite.

**Narrow the scope? Slightly.** Trim the two parts that most duplicate mature tools and most dilute the "thin layer" identity: **`directory`** (overlaps OpenFGA — pick one model or lean on the authz backend) and **`kernel`/`plugins`** (unproven; PydanticAI/pluggy already do this). Everything else earns its place.

**Split the project? No.** The single-distribution-with-extras consolidation was the right structural decision. Keep it.

**Rewrite part of it? Only `durable_langgraph.py`'s resume path** should be extracted and hardened — and only because it's the one real complexity/risk concentration.

**Adopt existing libraries instead? You already do** — correctly. The discipline to wrap LiteLLM/LangGraph/Temporal/mem0/OpenFGA rather than reimplement them is the project's biggest strength. Hold that line; resist the `directory`/`kernel` urge to build.

**The strongest possible version of this project:** the boring, reliable substrate every multi-tenant agent platform reaches for — `pip install coactra`, one `CoactraScope`, durable scoped `WorkOrder`s, swappable memory/workspace/workflow/org ports, and a 5-year compatibility promise on a *small, frozen* facade surface. Thin, typed, audited, honest.

**What to do next (in order):**
1. **Fix the `API_INDEX`/agent-compat defect and add `test_docs_imports`.** (Restores doc trust; half a day.)
2. **Single-source the version; refresh/flag the stale maintainer docs.**
3. **Make the breaking surface decisions now** — `CoactraScope` everywhere, demote `Kernel`, pick one `directory` model — *before* users depend on them.
4. **Close the conformance/CI gap** for workspace/org/workflow/routers + optional-extra lanes.
5. **Then** tag `v0.1.0` and publish.

This is a project worth finishing. The hard part — clean architecture and honest boundaries — is already done. The remaining work is **discipline, not invention.**
