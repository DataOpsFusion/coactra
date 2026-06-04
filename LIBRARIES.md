# Library Map

Standalone, `pip install`-able libraries. Each has **one job**, a clean public
interface, and its own tests. Built clean-room (not lifted from homelab-mcp).
The main project later just installs + imports the ones it needs.

> **CURRENT SHAPE:** six capability distributions plus the lightweight `coactra`
> convenience installer. The sibling libraries remain standalone; `coactra-agent` consumes
> them through ports and optional `coactra.agent.integrations`. Run `make test` from the
> repository root for the package-by-package suite. Each library has a `README.md` charter
> and a `DESIGN.md` spec.

## Installation

Install only the capability you need, or use the umbrella extras for convenience:

```bash
pip install coactra[memory]
pip install coactra[orchestration]
pip install coactra[agent]
pip install coactra[all]
```

The umbrella distribution contains no business logic. Direct installs such as
`pip install coactra-memory` remain supported.

## Design philosophy (north star — applies to every library, including future ones)

- Each library is a **thin orchestration layer with a generalized interface over
  best-of-breed existing libraries.** Wire them cleverly; never re-implement what a
  dependency already does.
- The value is the **clean wiring + swappable backend** — the libraries must not
  tangle on top of each other.
- **The set is open-ended.** Six is the current start. New libraries get added for new use
  cases, each following the same rules.
- Before adding a library, prove the gap: if an existing library already does it
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
fix." These six libraries are built **independently** to fix that: each is the
**universal interface for one capability**, standalone and swappable, then re-imported
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

**Escalation chain — `orchestration.workflow` → `organization` → a decider.**
- `orchestration.workflow` is dynamic; when it hits something it can't decide on its own, it raises
  an **escalation**.
- `organization` provides the chain — the escalation walks **up the hierarchy**.
- It keeps going up until a **decider** resolves it: a **human (you)** or, higher
  still, the **SOTA model**. Every chain terminates in a human / SOTA decision
  authority. `orchestration.workflow` triggers it, `organization` routes it, the top decides.

**`agent` = composition/policy layer, not a new protocol.**
- A2A (v1.0.x, 2026) is already mature (tasks, multi-turn, streaming, push, artifacts)
  and MCP already supports live tool changes (`tools.listChanged`, FastMCP live
  mounting). So `agent` builds the *collaboration policy + session orchestration* ABOVE
  them — it does NOT fork the protocols. "Direct agent talk" = policy over A2A.

**`memory` vs `lib-ai` reasoning-capture — NO overlap.**
- `memory` learns from the **conversation** — summaries, lessons, what happened.
  (Source = the interaction.)
- `lib-ai` reasoning-capture records the **model's OWN reasoning** — how it thought
  through a problem. (Source = the model's internal reasoning.)
- Different source, different data. They do **not** share a store.

### What each wraps and the gap it fills

| Lib | Wraps (existing) | The gap it fills |
|-----|------------------|------------------|
| lib-ai | openai-sdk, litellm, instructor | reasoning capture-replay (genuinely empty); model-calling is not |
| memory | mem0, graphiti/zep, letta, qdrant, neo4j | backend-neutral **connector SPI** (capability negotiation + lossy export); engines already consolidate from convos — don't replace |
| workspace | Daytona, E2B, OpenHands, Docker, local fs | control layer ABOVE persistent sandboxes: desk/files/CLI-policy/handoff/capability-manifest (providers persist state; none package the "desk") |
| orchestration | langgraph, temporal, prefect, DBOS, Temporal, Dapr Workflow, fsspec, A2A SDK, CloudEvents, OpenTelemetry | one package for reusable procedures and durable work orders; mature runtimes remain injectable |
| organization | sqlmodel (roles like crewai/autogen) | **multi-tenant flat fleet** + membership/isolation as a standalone directory; hierarchy/departments optional; no workflow execution inside |
| agent | openai-agents-sdk, a2a-sdk (v1.0.x), fastmcp, MCP-auth/RFC 8693 | session-level composition/policy ABOVE mature protocols: mid-session mounting, conflict/cache handling, delegated on-behalf-of identity (no token passthrough) |

Genuinely novel cores: **lib-ai's reasoning-replay** and **the un-tangled composition
itself**. The rest is "better seams over a crowded field" — worth building, but don't
reinvent mem0/langgraph by accident.

> **Design verdict:** `workflow` + `work` now ship as `coactra-orchestration`.
> Headline: wrap the solved layers (model calls, memory engines, sandboxes, MCP/A2A
> protocols); build thin connector, composition, and policy layers on top. Nothing here
> re-implements a backend; the value is the small contracts between them. See
> [docs/INTERFACES.md](docs/INTERFACES.md) for the application-facing API map.

## The six

| # | Library | One job | Depends on | Notes |
|---|---------|---------|------------|-------|
| 1 | **coactra-ai** | The model brain. Call LLMs + the reasoning-reuse idea: capture how a model reasoned through a problem and replay it next time instead of re-reasoning. | — | Foundation. The differentiator. Everything else uses it. |
| 2 | **coactra-memory** | Long-term facts. Write "what happened / what was learned", recall later. | — | Persistent knowledge store + retrieval. |
| 3 | **coactra-workspace** | **Persistent agent desk.** Files/state/CLI that persist across sessions (ephemeral mode optional). | — | A place the agent lives — not disposable scratch. |
| 4 | **coactra-orchestration** | Procedures plus durable work orders. Declarative recipes, real-job lifecycle, leases, retries, artifacts, decisions, and audit events. | — | One coherent control surface; execution remains delegated to mature runtimes. |
| 5 | **coactra-organization** | The company model. Roles, hierarchy, reporting, delegate / escalate / hire. | — | Who's who. |
| 6 | **coactra-agent** | The runtime that wires 1–6 into a working agent. **MCP (tool transport) and A2A (agent-to-agent wire) live in here** as plumbing — not separate libs. | all of the above | Wraps an LLM SDK (OpenAI) + the transports. Only lib that depends on everything. |

## Dependency shape

```
                lib-ai            (foundation)
               /  |   \
         memory workspace orchestration organization     (siblings — independent capabilities)
               \  |   /  /            /
                 agent  ────────────         (wires everything; holds MCP + A2A plumbing)
```

memory / workspace / orchestration / organization are **siblings** — none depends on the
others. They're just capabilities `agent` picks up. Only `agent` depends on
everything. No circular dependencies.

**Build order (bottom-up):** `lib-ai → memory + workspace → orchestration + organization → agent`

## Open design questions (deferred — not deciding yet)

- **lib-ai reasoning-reuse boundary.** When lib-ai "captures reasoning so it doesn't
  re-reason," what does the captured thing become? Three candidates, to resolve when
  we design lib-ai in depth:
  - *Producer* — lib-ai emits an `orchestration.workflow` + writes facts to `memory`, owns no store. (Keeps libs clean.)
  - *Own DB* — lib-ai keeps its own (problem → cached reasoning) store. (Risks 3 overlapping stores.)
  - *Cache layer* — just memoize (problem-hash → output). (Smallest scope.)
- **MCP gap.** FastMCP feels under-supported for some intended features. Folded into
  `agent` for now; revisit if the gap forces its own layer.

## Next step

Add production-backed adapters one at a time under integration tests. The core seams now exist; the next work is wiring real services behind them and keeping those adapters under conformance tests.

## Production seams added

The default installs remain small and offline-friendly. Production deployments can opt into:

- `coactra-orchestration`: async `WorkflowEngine.start/resume`, durable approval records,
  `DurableOrchestrator`, reviewable `ExecutionPlan` -> `ExecutionReceipt`, MCP Tasks
  translation, reviewed procedure promotion, work-store conformance probes, and
  tenant-routed work/procedure/runtime backends.
- `coactra-organization`: `AsyncPostgresOrgStore`, full directory metadata round trips,
  archived principals, audit attribution, generic `Authorizer`, optional OpenFGA bridge,
  and `TenantOrgStoreRouter`.
- `coactra-agent`: real RFC 8693 `KeycloakExchanger`, per-request audience/scopes,
  cached async token exchange, token-exchanger conformance probes, and `TenantAgentRouter`.
- `coactra-workspace`: dated journal rotation, `TenantWorkspaceBackendRouter`, and an optional
  office profile with memory, organization ACL, MCP recall, and workflow-drafting integrations.
- `coactra-ai`: dependency-light token counting, optional tiktoken, and
  `TenantReasoningStoreRouter`.
- `coactra-memory`: `TenantMemoryBackendRouter`, scoped `AuthorizedMemory`, and backend
  conformance probes.

Pool mode remains the default. Each `Tenant*Router` is an opt-in silo-isolation adapter:
a tenant id selects one cached physical backend instance.

## Compatibility policy

The superseded `coactra-work` and `coactra-workflow` distributions were removed. The
`coactra-orchestration` wheel intentionally keeps thin `coactra.work` and
`coactra.workflow` Python aliases so existing homelab imports can migrate dependency-first.
Other flat modules that remain are similarly thin compatibility imports, not duplicate
implementations. Remove them only in a future breaking release.

## Adapter maturity matrix

| Package | Adapter | Maturity | Notes |
|---|---|---|---|
| coactra-workspace | LocalFilesystemBackend | reference | File confinement; local exec is opt-in and not a sandbox. |
| coactra-workspace | DaytonaBackend / E2BBackend / OpenHandsBackend | stub | Names the intended seam only; not production implementations. |
| coactra-agent | KeycloakExchanger | implemented | RFC 8693 token exchange with no token passthrough; async variant available with `coactra-agent[oauth]`. |
| coactra-agent | OfficialA2ATransport | implemented | Official SDK bridge; import from `coactra.agent.adapters`. |
| coactra-orchestration | DBOS / Temporal / Dapr dispatchers | experimental | Thin dispatch bridges; the durable work ledger remains Phase 3. |
