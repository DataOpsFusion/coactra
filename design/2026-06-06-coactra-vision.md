# Coactra — System Vision (alpha)

**Date:** 2026-06-06  **Status:** all domains designed — Agent · Workflow · Team · workspace (+ memory, ai). Specs in `design/`. Ready for implementation planning.

The whole library is **three nouns**, plus an internal engine and two agent capabilities. Everything a developer touches goes through the `Agent` door.

## The three nouns

| Noun | What it is | Today's code → rename | Status |
|------|-----------|----------------------|--------|
| **Team** | Who exists & how they relate — agents, hierarchy, who-may-talk, tenant, the capability roster | `coactra.directory` (+ drop `organization`) → `coactra.team` | ✅ `design/2026-06-06-team-design.md` |
| **Agent** | One worker — thinks, uses tools + MCP, has memory; exposed via A2A | `coactra.agent` (the SDK `Agent`) | ✅ `design/2026-06-06-agent-api-design.md` |
| **Workflow** | A playbook + the manager running it — steps, assign to agents, track to done, retries, approvals | `coactra.jobs` = `work` + `workflow` (+ drop `orchestration`) → `coactra.workflow` | ✅ `design/2026-06-06-workflow-design.md` |

Collapsed away: `work`, `jobs`, `orchestration`, `organization` were extra names for the above. "Durable / retries / approvals / a work order" = **properties of a Workflow run**, not separate domains.

### Supporting (not separate domains)
- **ai** — internal engine: litellm routing + thinking-model handling. Users never import it; `Agent` and the planner use it. ✅ built.
- **memory** — agent capability, `Agent.create(memory="graphiti")`. Pure connector over graphiti/mem0; **automatic** recall+remember (coactra never ranks/stores). ✅ designed (in the Agent spec).
- **workspace** — agent capability, `Agent.create(workspace="./desk")`. Surfaces **as tools** (`read_file`/`write_file`/`list_files`/`run`); the model uses the desk as part of its task; `run` is allowlist-gated. Most optional capability — many agents won't set it. ✅ designed.
- **auth** (cross-cutting) — coactra is an OAuth 2.1 client + MCP-gateway consumer: a **token's scopes** slice the agent's tools (no manual MCP list); **skills** are published as an A2A **Agent Card** (curated, no creds); token source is pluggable (OIDC fetch+refresh / SPIFFE later); fine-grained authz via a policy seam (OpenFGA/AuthZEN). Aligned to MCP OAuth 2.1 + A2A. ✅ `design/2026-06-06-auth-design.md`.

## How they compose (the company model)

```
Team      = the org chart   → who's here, who-reports-to-whom, who-may-talk, tenant
Agent     = an employee     → thinks, tools + MCP, memory   (the worker)
Workflow  = a playbook + the manager running it
            → plan/pick steps, assign each to an Agent from the Team,
              track to done, retry, pause for approval, delegate across the Team (A2A)
```

A goal arrives → **Workflow** plans or picks a playbook → assigns each step to an **Agent** chosen from the **Team** → drives every step to done (retry/approve) → an Agent step may delegate to a teammate (A2A, same Team). That's the entire system.

## Public surface (the one door)

`from coactra import Agent` → `Agent.create(model, name, tenant, gateway=, auth=, tools=[local funcs], memory, workspace, peers, skills, instructions)` → `run / send().stream()`. **`gateway=`+`auth=` is the primary MCP path** (the token's scopes slice the tools); a bare `mcp(url)` is the exception. Full detail in `design/2026-06-06-agent-api-design.md`.

## Build order

1. **Agent core** — top-level export, `mcp()` + tool expansion, memory connector *(spec done)*
2. **workspace** — quick (surface as read/write/run tools)
3. **Team** — policy (who-may-talk) + capability roster (`skills=`), unlocks A2A peers/discovery
4. **Workflow** — the big one: how a playbook is defined and run across the Team

## Brownfield note

The renames (`directory`→`team`, `jobs`/`work`/`orchestration`→`workflow`) touch homelab, which imports `coactra.directory` and `coactra.jobs.workflow`. Alpha = we don't keep deprecated shims, but homelab needs a sync pass — mechanics in `design/2026-06-06-rename-migration.md`.

## Additional specs
- `2026-06-06-auth-design.md` — auth/identity: OAuth 2.1 client + gateway tool-slicing + A2A Agent Cards
- `2026-06-06-operations-design.md` — observability/tracing (OpenTelemetry) + error handling
- `2026-06-06-rename-migration.md` — `jobs`→`workflow` / `directory`→`team` mechanics
- `2026-06-06-review-refinements.md` — v2 tightening from external review (lean Team · gateway-primary · structured skills · internal run-ledger · **candidate** playbooks not auto-save · memory guardrails · workspace gating)
