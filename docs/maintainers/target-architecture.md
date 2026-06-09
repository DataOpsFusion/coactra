# Target Architecture

Coactra's target architecture is **Team · Agent · Workflow** — a small public
surface with one assembly door. The library wraps mature runtimes (LangGraph,
Temporal, Graphiti, mem0, LiteLLM, MCP, A2A) rather than reimplementing them.
Coactra owns the policy, tenancy, scope, capability roster, and connector
contracts that sit above those engines.

**Core decisions:**

- One public assembly door: `from coactra import Team, Scope, Policy, Workflow`
- `Team(scope=..., policy=...)` owns agent registration, skill catalogs, workflow catalogs, and routing
- `team.add_agent(...)` is the only public construction path for runtime agents
- `Workflow(steps=[...])` binds to `requires_skill`, with direct `agent=` pinning only as an override
- `ai` remains an internal engine layer, not a public package identity
- `memory` and `workspace` stay adapter-backed capabilities governed by Team policy
- Auth follows OAuth 2.1 / MCP gateway / A2A Agent Cards standards

The authoritative source for the full architecture — the Team-first execution
model, build order, brownfield notes, and supporting specs — is the system
vision document:

**[design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md)**

The external-review refinements that tighten standards alignment, Team-first
assembly, gateway-primary auth, structured Skills, and workspace security:

**[design/2026-06-06-review-refinements.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-review-refinements.md)**
