# Target Architecture

Coactra's target architecture is **Agent · Team · Workflow** — three nouns, one
public door (`from coactra import Agent`). The library wraps mature runtimes
(LangGraph, Temporal, Graphiti, mem0, LiteLLM, MCP, A2A) rather than reimplementing
them. coactra owns the policy, tenancy, scope, capability roster, and connector
contracts that sit above those engines.

**Core decisions:**

- One public entry point: `from coactra import Agent, Team, Workflow`
- `Agent.create(...)` — named capabilities, no DI ceremony
- `Team([...])` — lean agent registry + capability matcher + who-may-talk policy
- `Workflow(steps=[...])` — playbook + durable run + approvals
- `ai` is the internal engine (never imported by users)
- `memory` and `workspace` are agent capabilities, not standalone domains
- Auth follows OAuth 2.1 / MCP gateway / A2A Agent Cards standards

The authoritative source for the full architecture — the three-noun model, build
order, brownfield notes, and supporting specs — is the system vision document:

**[design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md)**

The external-review refinements that tighten standards alignment, lean Team,
gateway-primary auth, structured Skills, and workspace security:

**[design/2026-06-06-review-refinements.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-review-refinements.md)**
