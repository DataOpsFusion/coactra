# coactra — Multi-Tenant / Pluggable-Architecture Audit

> **Question this answers:** *Is my code wrong, or does my current library just not yet
> satisfy the multi-tenant needs?* And: *can homelab-mcp drop its custom code and use these
> libraries instead?*
>
> **Method:** 7 parallel per-library code audits (not docstrings — actual source), each scored
> on a 2-dimensional rubric so the two halves of the question stay separate:
> - **Seam present?** = *does it satisfy the need* (capability) — Solid / Partial / Missing / N/A
> - **Broken / leaks?** = *is the code wrong* (correctness) — Clean / Risk / Broken
>
> Date: 2026-06-01. Scope of "tenancy" tested across 4 axes: **isolation model** (pool / silo /
> bridge), **fleet topology** (flat / hierarchical / swarm), **host integration** (adapt to a
> host's own tenant/org/auth), **deployment shape** (single / SaaS / dedicated / on-prem).

## Headline verdict

**The code is NOT wrong. The architecture is right, consistent, and mostly clean.**

Every library independently converged on the **same seam pattern**:
`Scope` value object (tenant_id + namespace) → backend **SPI Protocol** → `factory` / DI →
optional `adapters/`. Tenant scope is threaded through the store APIs; a module-level
mutable-singleton grep across all 7 libs came back **empty** (no global tenant-spanning
caches — the classic multi-tenant leak is structurally absent).

The true state is a **third thing**, distinct from both "wrong" and "doesn't satisfy":

> **Migration-in-flight.** The libraries are mid-move from flat modules → structured
> packages (`domain/`, `backends/`, `repository/`, `runtime/`). The flat top-level modules are
> now **deprecated compatibility shims** that only re-export; the live code is the structured
> packages. This is why the tree looks duplicated — it is a half-finished refactor, not
> accidental copy-paste.

So: **you do not start over.** You finish the migration, fix **3 concrete bugs**, and decide
whether you need the **one consistent missing capability** (silo isolation — see below).

## The lib × axis matrix

Seam present (capability) / Broken-leaks (correctness):

| Library | Isolation | Topology | Host integration | Deployment | State |
|---|---|---|---|---|---|
| **lib-ai** | Solid / Clean | N/A | Solid / Clean | Solid / Clean | **solid** |
| **memory** | Solid / **Risk** | N/A | Solid / Clean | Solid / Clean | migration-in-flight |
| **workspace** | Solid / **Broken** | N/A | Solid / Clean | Solid / Clean | migration-in-flight |
| **workflow** | Partial / Clean | Solid / Clean | Solid / Clean | Solid / Clean | migration-in-flight |
| **organization** | Solid / **Risk** | Solid / Clean | Partial / Risk | Solid / Risk | migration-in-flight |
| **work** | Solid / Clean | Partial (N/A) | Solid / Clean | Solid / Clean | **solid** |
| **agent** | Solid / Clean | Solid / Clean | Solid / Clean | Solid / Clean | **solid** |

`agent`, `work`, and `lib-ai` are clean across the board. The composition layer (`agent`) — the
one that actually has to "plug into many architectures" — is the **strongest**: all six sibling
ports are genuine `@runtime_checkable` Protocols, identity is pluggable, no token passthrough,
mount state is per-instance.

## The 4 axes, read across all libs

### 1. Isolation — pool works everywhere; **silo is the one consistent gap**
- **Pool** (one shared store keyed by tenant) is the **native, working** model in every lib —
  in-memory backends partition by `Scope.key`; tenant is threaded through every store read/write.
- **Silo** (a *different physical backend per tenant* — separate DB, separate sandbox provider) is
  **reachable but not shipped anywhere.** The DI seam exists (you can inject a per-tenant store),
  but **no library has a factory that binds a backend per tenant** — `make_*_store(config)` keys on
  backend URL, not on tenant. If homelab-mcp needs hard physical per-tenant isolation, *this is the
  single thing to add*, and it's the same small pattern in every lib (a routing/factory layer).
- **Bridge** (shared infra, separated schema) falls out of pool + namespace; no extra work.

### 2. Fleet topology — covered
`organization` does flat ↔ hierarchical properly: flat fleet is the working baseline (parent=None),
hierarchy is additive (`add_child`/`move`/`manager`), and the AD-style permission inheritance
(block-inheritance + per-member override + deny-beats-allow) was **verified by reading the
algorithm**, not the docstring. `agent` adds tenant-qualified, deniable collaboration over A2A.

### 3. Host integration — `agent` exemplary, `organization` the weak spot
`agent`'s six sibling ports are true Protocols a host implements structurally (no sibling-guts
imports); identity is a swappable `TokenExchanger` Protocol with a Keycloak slot. The weak spot is
`organization`: its `OrgStore` Protocol **traffics in concrete SQLModel row types**, so a host
backing it with their own directory/IdP must materialize those exact rows (type coupling at the SPI
boundary).

### 4. Deployment shape — clean
No module-level mutable singletons anywhere; config is injected via constructors/factories; services
are stateless apart from injected deps. The in-memory default stores (`work`, `workflow`,
`organization`) are **single-process by construction** — a deployment *constraint*, not a bug; swap
the Protocol-backed store for a durable one in multi-process deployments.

## The 3 concrete bugs (correctness — "code is wrong" here, narrowly)

1. **workspace — `exec` is not filesystem-confined (isolation leak).**
   File ops (`read/write/delete`) are confined to the desk root via `_resolve()`
   (`backends/local.py:32-37`), but `exec` only sets `cwd=root` with **no jail**
   (`backends/local.py:59-67`). Verified empirically: tenant A's
   `run(["cat","../../tenantB/agentX/secret.txt"])` reads tenant B's file; absolute paths escape
   too. The Protocol docstring claims confinement is "part of the contract" for every method
   (`backends/base.py:6-8`) — `exec` violates it. *Inherent to a local subprocess backend*; real
   backends (Daytona/E2B containers) enforce it. **Also:** `Scope` validates only `min_length=1`
   (`scope.py:19-20`), so a `tenant_id` containing `../` escapes the root — sanitize scope
   components if they can come from untrusted input. (Note: workspace's `Scope` is
   `(tenant_id, agent_id)`, not `(tenant_id, namespace)` like the siblings.)

2. **memory — mem0 `dump`/export is broken against the real engine.**
   `Mem0Backend.dump` passes `user_id=` as a **top-level** kwarg to `get_all`
   (`backends/mem0.py:105`), but installed mem0 2.0.4 accepts scoping only via `filters=` and
   explicitly rejects top-level entity params → `ValueError`. `recall` (`mem0.py:99`) and `add`
   (`mem0.py:93`) use the correct conventions, so the inconsistency is internal to the adapter.
   **Masked by tests:** the fake mem0 client swallows any kwargs and the isolation test only
   exercises the in-process backend, so CI never runs the real mem0 scoping contract. graphiti
   scoping is correct.

3. **organization — cross-tenant member placement is not guarded (isolation risk).**
   `assign` (`repository/sqlite_store.py:70-99`) and `place_member` (`:452-486`) validate
   `member_id`/`seat_id` against the tenant but **never validate `department_id`/`node_id`** — a
   member can be placed onto *another tenant's* OU node with no `CrossTenantError`, even though the
   sibling `grant_node` (`:349-353`) does check. The Protocol docstring promises scoping is "part of
   the contract, not the caller's discipline" (`repository/store.py:8`) — unmet on this path.

## The structural debt (organization — the most central lib carries the most)

`organization` runs **two parallel, half-bridged models**: the v0.2 OOP OU-tree (`domain/`) and the
legacy SQLModel directory (`models.py`), both publicly exported. `save_org`/`load_org` bridge only
nodes + members + seats + grants + overrides — `ReportingEdge`, `EscalationRoute`, `owner_of`, and
`PolicyRef` live **only** in the legacy store with no domain equivalent. This is an **unfinished
migration, not a designed dual API**. It is also the only lib without a `Scope` value object (tenant
travels via `Organization.root(tenant=...)` and `tenant_id` columns) — internally consistent, but
asymmetric with the four `Scope`-based siblings. Save is non-atomic (per-call sessions, no version
column → last-writer-wins under concurrency).

## Lower-priority debt (non-blocking)
- **Migration cleanup:** flat shims still ship in `lib-ai` / `workspace` / `workflow` /
  `organization`; `workflow/PLAN.md` still documents the old flat layout (stale).
  `organization/factory.py:14` imports `OrgStore` from the *shim* path, keeping it on the live path.
- **lib-ai `chroma.py`:** latent runtime bug — `put` nests `meta` dict into Chroma metadata, which
  only accepts scalars (optional adapter; not a tenant leak).
- **work `WorkStore.save`** omits an explicit `scope` arg (`store.py:19`) — relies on `order.scope`
  integrity + each backend re-implementing the in-memory cross-scope guard.
- **agent** redefines `Scope` in three sibling-flavored shapes, translated at the integration
  boundary (correct for standalone distributions, but duplicated modeling to keep aligned).

## What this means for the ultimate goal (replace homelab-mcp custom code)

**Yes — the libraries are ready enough to absorb homelab-mcp's custom code**, which is exactly what
the `_workspace/` integration reports (memory swap, org ACL, workspace/lib-ai/workflow/agent seams)
already prototyped. The architecture satisfies the need. Before/while swapping:

1. **Fix the 3 bugs** — they are small and localized (workspace exec confinement / scope sanitize,
   memory mem0 `dump` → `filters=`, organization placement tenant-check). The memory + workspace
   ones matter most if homelab-mcp tenants are mutually untrusted.
2. **Decide pool vs silo.** If homelab-mcp is fine with one shared store keyed by tenant (pool),
   you can swap today. If it needs *physical* per-tenant isolation (silo), add the per-tenant
   routing/factory layer first — same small pattern in each lib.
3. **Finish organization's migration** (or consciously pick one model) before leaning on it hard —
   it's the most central to tenancy and carries the most debt.
4. **Add real-engine contract tests** for memory (mem0/graphiti) so adapter drift like bug #2 stops
   passing CI on fakes.

**Bottom line:** not wrong, not start-over. A correct, consistent, seam-based design that is
~80% there — finish the in-flight migration, fix three bounded bugs, and add silo routing only if
your tenancy model actually demands physical isolation.
