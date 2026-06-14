# Library Map

One `pip install`-able distribution (`coactra`) made of capability modules. Each
capability has **one job**, a clean public interface, and its own tests. Built
clean-room (not lifted from homelab-mcp). The main project installs `coactra` and
imports the modules it needs.

> **CURRENT SHAPE:** a single `coactra` distribution; capabilities are selected via
> extras (`pip install "coactra[memory,workflow]"`). The capability modules stay
> decoupled; `coactra.agent` consumes them through ports and optional
> `coactra.agent.integrations`. Run `make test` from the repository root for the
> default non-live suite; live backend checks run through `make live-check`.
> Maintainer design notes live under the `maintainers` section of this docs site.
## Installation

One distribution, capabilities via extras:

```bash
pip install "coactra[memory]"
pip install "coactra[memory,workflow]"
pip install "coactra[agent]"
pip install "coactra[all]"
```

The base install (`pip install coactra`) carries the dependency-light core
(including jobs/`WorkManager`); extras add the optional capability and backend
dependencies. There are no separate `coactra-*` distributions.

## Design philosophy (north star — applies to every library, including future ones)

- Each library is a **thin orchestration layer with a generalized interface over
  best-of-breed existing libraries.** Wire them cleverly; never re-implement what a
  dependency already does.
- The value is the **clean wiring + swappable backend** — the libraries must not
  tangle on top of each other.
- **The set is open-ended.** New capabilities get added for new use
  cases, each following the same rules.
- Before adding a capability, prove the gap: if an existing library already does it
  cleanly, depend on it instead. Build only where the *generalized, non-tangling*
  interface genuinely doesn't exist yet.

### Why a standalone repo, and what the gap actually is

The platform is a **multi-tenant system for running fleets of AI agents**. Each tenant
runs its own fleet; the baseline shape is a **flat fleet** (no hierarchy). A SOTA model
(Claude/Codex, via the *existing* MCP gateway) and/or a human can drive a fleet. The
control surface to the SOTA model **already exists** — that is not the missing piece.

Hierarchy / departments / "run it like a company" is **one OPTIONAL topology** on top
of the flat fleet, never baked in.

The missing piece is the **fleet layer**: many agents working together with clean,
universal interfaces. Today that lives only as *customization inside homelab-mcp* — the
pieces overlap, there's no universal interface, so it "turns ugly fast and is hard to
fix." These capabilities are built **independently** to fix that: each is the
**universal interface for one capability**, decoupled and swappable, then re-imported
into homelab-mcp.

**Multi-tenancy is cross-cutting** — every library is tenant-scoped/isolated (memory,
workspace, orchestration, organization, agent), not just `organization`. Tenant isolation is
a first-class concern in each interface, not an add-on. (Mirrors homelab-mcp's ADR-004
`tenant_id` work.)

Design stance that makes this both flexible AND codeable:
- **Flexibility lives at the seams, not the core.** Each lib has a small opinionated
  core with ONE working default + a `Protocol` interface so any backend can be swapped.
  "Give people the power" = swap backends, not configure a thousand knobs.
- **Opinionated default, open edge.** Works out of the box; advanced users swap.
- **Power to agents = remove artificial limits + mount capabilities at runtime**, not
  endless config.

### Boundaries (who owns what — resolves the overlaps)

**Escalation chain — `workflow` → `organization` → a decider.**
- `workflow` is dynamic; when it hits something it can't decide on its own, it raises
  an **escalation**.
- `organization` provides the chain — the escalation walks **up the hierarchy**.
- It keeps going up until a **decider** resolves it: a **human (you)** or, higher
  still, the **SOTA model**. Every chain terminates in a human / SOTA decision
  authority. `workflow` triggers it, `organization` routes it, the top decides.

**`agent` = composition/policy layer, not a new protocol.**
- A2A (v1.0.x, 2026) is already mature (tasks, multi-turn, streaming, push, artifacts)
  and MCP already supports live tool changes (`tools.listChanged`, FastMCP live
  mounting). So `agent` builds the *collaboration policy + session orchestration* ABOVE
  them — it does NOT fork the protocols. "Direct agent talk" = policy over A2A.

**`memory` vs `coactra.ai` reasoning-capture — NO overlap.**
- `memory` learns from the **conversation** — summaries, lessons, what happened.
  (Source = the interaction.)
- `coactra.ai` reasoning-capture records the **model's OWN reasoning** — how it thought
  through a problem. (Source = the model's internal reasoning.)
- Different source, different data. They do **not** share a store.

### What each wraps and the gap it fills

| Lib | Wraps (existing) | The gap it fills |
|-----|------------------|------------------|
| coactra.ai | openai-sdk, litellm, instructor | reasoning capture-replay (genuinely empty); model-calling is not |
| memory | mem0, graphiti/zep, letta, qdrant, neo4j | backend-neutral **connector SPI** (capability negotiation + lossy export); engines already consolidate from convos — don't replace |
| workspace | Daytona, E2B, OpenHands, Docker, local fs | control layer ABOVE persistent sandboxes: desk/files/CLI-policy/handoff/capability-manifest (providers persist state; none package the "desk") |
| orchestration | langgraph, temporal, prefect, DBOS, Temporal, Dapr Workflow, fsspec, A2A SDK, CloudEvents, OpenTelemetry | one package for reusable procedures and durable work orders; mature runtimes remain injectable |
| organization | sqlmodel (roles like crewai/autogen) | **multi-tenant flat fleet** + membership/isolation as a standalone directory; hierarchy/departments optional; no workflow execution inside |
| agent | openai-agents-sdk, a2a-sdk (v1.0.x), fastmcp, MCP-auth/RFC 8693 | session-level composition/policy ABOVE mature protocols: mid-session mounting, conflict/cache handling, delegated on-behalf-of identity (no token passthrough) |

Genuinely novel cores: **coactra.ai's reasoning-replay** and **the un-tangled composition
itself**. The rest is "better seams over a crowded field" — worth building, but don't
reinvent mem0/langgraph by accident.

> **Note:** the workspace control layer ships only the reference `LocalFilesystemBackend`
> today; provider integrations (Daytona/E2B/OpenHands, etc.) are intended seams, not
> shipped backends. **Design verdict:** procedures + the work-order ledger now ship in `coactra.workflow`.
> Headline: wrap the solved layers (model calls, memory engines, sandboxes, MCP/A2A
> protocols); build thin connector, composition, and policy layers on top. Nothing here
> re-implements a backend; the value is the small contracts between them. See
> [API Index](../API_INDEX.md) for the application-facing API map.

## The capabilities

| # | Module / extra | One job | Depends on | Notes |
|---|---------|---------|------------|-------|
| 1 | **coactra.ai** (`[ai]`) | The model brain. Call LLMs + the reasoning-reuse idea: capture how a model reasoned through a problem and replay it next time instead of re-reasoning. | — | Foundation + differentiator. *Intended* reasoning substrate; today only `coactra.memory`'s optional Graphiti backend imports it — the others stay decoupled by design. |
| 2 | **coactra.memory** (`[memory]`) | Long-term facts. Write "what happened / what was learned", recall later. | — | Persistent knowledge store + retrieval. |
| 3 | **coactra.workspace** (`[workspace]`) | **Persistent agent desk.** Files/state/CLI that persist across sessions (ephemeral mode optional). | — | A place the agent lives — not disposable scratch. |
| 4 | **coactra.workflow** (`[workflow]`) | Procedures plus durable work orders. Declarative recipes, real-job lifecycle, leases, retries, artifacts, decisions, and audit events. | — | One coherent control surface (in the base package); execution remains delegated to mature runtimes. |
| 5 | **coactra.team** (`[team]`) | The company model. Roles, hierarchy, reporting, delegate / escalate / hire. | — | Who's who. |
| 6 | **coactra.agent** (`[agent]`) | The runtime that wires 1–6 into a working agent. **MCP (tool transport) and A2A (agent-to-agent wire) live in here** as plumbing. | all of the above | Wraps an LLM SDK (OpenAI) + the transports. Only module that depends on everything. |

## Dependency shape

```
              coactra.ai          (foundation)
               /  |   \
   memory workspace jobs directory     (capability modules — independent)
               \  |   /  /        /
              coactra.agent  ───────       (wires everything; holds MCP + A2A plumbing)
```

`coactra.memory` / `coactra.workspace` / `coactra.workflow` / `coactra.team` are
**independent capability modules** — none depends on another's core. The only
cross-module coupling is optional and confined to `integrations/` modules (e.g.
`coactra.workspace.integrations` importing `coactra.memory` / `coactra.team`),
never pulled in by the base install. They're capabilities `coactra.agent` picks up;
only `coactra.agent` depends on everything. No circular dependencies.

**Layering (bottom-up):** `ai → memory + workspace → jobs + directory → agent`

## Open design questions (deferred — not deciding yet)

- **coactra.ai reasoning-reuse boundary.** When coactra.ai "captures reasoning so it doesn't
  re-reason," what does the captured thing become? Three candidates, to resolve when
  we design coactra.ai in depth:
  - *Producer* — coactra.ai emits an `workflow` + writes facts to `memory`, owns no store. (Keeps libs clean.)
  - *Own DB* — coactra.ai keeps its own (problem → cached reasoning) store. (Risks 3 overlapping stores.)
  - *Cache layer* — just memoize (problem-hash → output). (Smallest scope.)
- **MCP gap.** FastMCP feels under-supported for some intended features. Folded into
  `agent` for now; revisit if the gap forces its own layer.

## Next step

Add production-backed adapters one at a time under integration tests. The core seams now exist; the next work is wiring real services behind them and keeping those adapters under conformance tests.

## Production seams added

The base install remains small and offline-friendly. Production deployments can opt into:

- `coactra.workflow`: async `WorkflowEngine.start/resume`, durable approval records,
  `DurableOrchestrator`, reviewable `ExecutionPlan` -> `ExecutionReceipt`, MCP Tasks
  translation, reviewed procedure promotion, work-store conformance probes, and
  tenant-routed jobs/procedure/runtime backends.
- `coactra.team`: `AsyncPostgresOrgStore`, full directory metadata round trips,
  archived principals, audit attribution, generic `Authorizer`, optional OpenFGA bridge,
  and `TenantOrgStoreRouter`.
- `coactra.agent`: real RFC 8693 `KeycloakExchanger`, per-request audience/scopes,
  cached async token exchange, token-exchanger conformance probes, and `TenantAgentRouter`.
- `coactra.workspace`: dated journal rotation, `TenantWorkspaceBackendRouter`, and an optional
  office profile with memory, organization ACL, MCP recall, and workflow-drafting integrations.
- `coactra.ai`: dependency-light token counting, optional tiktoken, and
  `TenantReasoningStoreRouter`.
- `coactra.memory`: `TenantMemoryBackendRouter`, scoped `AuthorizedMemory`, and backend
  conformance probes.

Pool mode remains the default. Each `Tenant*Router` is an opt-in silo-isolation adapter:
a tenant id selects one cached physical backend instance.

## Alpha package policy

The root `coactra` API is the preferred application surface. Lower-level package roots
such as `coactra.workflow` and `coactra.team` is a lower-level implementation surface until their
code is moved fully into the final Agent / Team / Workflow vocabulary. Do not add alias
packages or compatibility wrappers for removed paths.

## Adapter matrix

| Module | Adapter | Notes |
|---|---|---|
| coactra.workspace | LocalFilesystemBackend | File confinement; local exec is opt-in and **not a sandbox** — use a remote/sandboxed backend for untrusted commands. |
| coactra.agent | KeycloakExchanger | RFC 8693 token exchange with no token passthrough; async variant available with `coactra[oauth]`. |
| coactra.agent | OfficialA2ATransport | Minimal outbound A2A bridge via `coactra.agent.adapters`. Inbound serving: use `a2a-sdk` directly. |
| coactra.workflow | DurableLangGraphEngine / TemporalEngine / PrefectEngine | `WorkflowEngine` adapters; durable resume requires explicit checkpointer/runtime configuration. |
| coactra.workflow | DBOS / Temporal / Dapr dispatchers | Experimental thin dispatch bridges; the Coactra ledger remains the source of truth. |
