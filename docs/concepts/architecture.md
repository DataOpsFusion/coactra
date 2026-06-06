# Architecture

Coactra is a **thin orchestration library**, not a monolithic agent framework. It owns the
wiring, policy, and identity contracts; durable execution is delegated to mature engines.

## The three nouns

Everything in the public surface maps to three nouns:

```
Team      = the roster        — who exists, who-may-talk, who-can-do-what
Agent     = a worker          — thinks, calls tools + MCP, remembers, is discoverable
Workflow  = a playbook runner — plans steps, assigns to Agents, drives to done
```

Think of it as a company model:

```
Team      = the org chart     → who's here, hierarchy, who may talk, tenant
Agent     = an employee       → thinks, tools + MCP, memory
Workflow  = a manager + playbook
            → assign each step to an Agent from the Team,
              track to done, retry, pause for approval, delegate peer-to-peer (A2A)
```

A goal arrives → **Workflow** picks or plans a playbook → assigns each step to an **Agent**
chosen from the **Team** → drives every step to done (retry/approve) → an Agent step may
delegate to a teammate via A2A within the same Team.

!!! info "Alpha: Agent is available; Team and Workflow are designed and coming"
    `Agent` is the shipped noun in 0.0.x. `Team` and `Workflow` are fully designed (see
    `design/` directory) and are the next build items. Pages in this docs site that describe
    `Team` and `Workflow` describe the design target, not current code.

## How they compose

### Agent (available now)

An Agent is the unit of work. It:

- accepts a model id (routed through litellm with thinking-model adaption)
- has a unified tool list — local Python functions + gateway-sliced MCP tools
- can hold memory (auto-recall/remember via a backend connector)
- can work against a file desk (workspace tools: read/write/list/run)
- publishes a curated skill roster as an A2A **Agent Card**
- is identified by `name=` and `tenant=`

The primary MCP path is `gateway=` + `auth=`: the token's OAuth scopes slice the
available tools. No manual tool enumeration. A bare `mcp(url)` is additive for local
or extra servers.

### Team (designed — coming)

A Team is a bag of Agents plus policy. It:

- holds the capability roster (aggregated from each Agent's `skills=`)
- evaluates who-may-talk (default: same tenant; pluggable to OpenFGA / AuthZEN)
- supports keyword (default) or semantic matching to route a step's `needs=` to the right agent
- optionally names a `manager` for hierarchy and escalation

A Team is optional: a single Agent needs no Team.

### Workflow (designed — coming)

A Workflow is a playbook of steps plus the manager that runs it across the Team. It:

- accepts an authored playbook (`Workflow(steps=[step(...), ...])`) or a goal string (`Workflow.run_goal("...")`)
- triages: a known goal reruns the saved playbook; a new goal plans one via the internal AI engine
- assigns each step to an Agent by name or by capability (matched against the Team roster)
- drives durably — checkpointing, retries, and approval pauses survive restarts
- saves planner-generated playbooks as **candidates** (not auto-promoted), preventing library poisoning

## Supporting subsystems

### ai (internal engine)

`coactra.ai` is the internal model engine — litellm routing, thinking-model handling
(`reasoning_content` fallback), structured output, and embeddings. Users never import it.
`Agent` and the Workflow planner use it internally.

### auth (cross-cutting)

Auth is not buried in one noun — it is cross-cutting across Agent, Team, and Workflow:

- **Token (JWT / OAuth 2.1):** carries identity (`sub` → name, tenant) and scopes.
- **Gateway:** verifies the token and slices the tool list to the scopes' allowed set.
- **Agent Card (A2A):** published when `expose=True`; contains the curated `skills=` roster,
  which scopes each skill needs, and `securitySchemes`. No credentials. Credentials are never
  in the card.
- **Token source:** `oidc(issuer, client_id, client_secret)` for client-credentials fetch and
  refresh; `token=jwt` for development; SPIFFE workload identity later.
- **Fine-grained authz:** Team's same-tenant default, pluggable to OpenFGA / OpenID AuthZEN.

Security invariant: **seeing ≠ calling**. Discovery exposes only the curated skills blurb;
every A2A delegation is still auth-gated (token exchange + policy).

### memory (agent capability)

`memory="graphiti"` connects the agent to a memory backend. Auto-recall runs on the user's
latest message; auto-remember runs after each turn. coactra is the connector — graphiti / mem0
own ranking and consolidation. coactra never runs its own vector store.

### workspace (agent capability)

`workspace="./desk"` surfaces a directory as agent tools: `read_file`, `write_file`,
`list_files`, `run`. `run` is allow-list gated. OWASP MCP risks (tool poisoning, secret
leakage, command injection) are first-class design concerns.

## Stack alignment

Coactra delegates to mature libraries at every layer:

| Layer | Delegates to |
|-------|-------------|
| Model calls | litellm + pydantic-ai |
| Structured output | pydantic-ai output types |
| Memory | graphiti / mem0 |
| Durable workflow execution | LangGraph (default) · Temporal · Prefect |
| MCP transport | MCP SDK (tools + gateway) |
| A2A protocol | A2A SDK (v1.0.x) |
| Auth | OAuth 2.1 / OIDC (client flow); Keycloak exchanger |
| Fine-grained policy | OpenFGA / OpenID AuthZEN |
| Observability | OpenTelemetry (GenAI semantic conventions) |

## Build order

The implementation follows this order:

1. **Agent core** — top-level export, tool expansion, gateway+auth, memory connector *(Slice 1 shipped: model + run/stream/structured; remaining: gateway/auth/memory/workspace/skills)*
2. **workspace** — surface file desk as agent tools
3. **Team** — capability roster + who-may-talk policy, unlocks A2A peer discovery
4. **Workflow** — playbook definition, triage, durable step execution across the Team

## Runtime delegation rule

Before adding orchestration code, classify it:

1. Coactra-specific policy or boundary → keep it.
2. Portable ledger/state vocabulary → keep it if it aids auditability across runtimes.
3. Generic retries, recovery, scheduling, state replay, or worker orchestration → use a runtime adapter (LangGraph / Temporal / Prefect).
4. Framework-specific API ergonomics → hide behind ports until the choice is proven.

See [Library Map](library-map.md) for the full module-by-module breakdown.
