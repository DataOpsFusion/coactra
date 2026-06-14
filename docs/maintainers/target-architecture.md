# Target Architecture

Coactra's target architecture is **Team · Agent · Workflow** - a small public surface with one
assembly door. The library wraps mature runtimes (Temporal, LangGraph, Graphiti, mem0,
LiteLLM, MCP, A2A) rather than reimplementing them. Coactra owns the policy, tenancy, scope,
capability roster, and connector contracts that sit above those engines.

**Core decisions:**

- One public assembly door: `from coactra import Team, Scope, Policy, Workflow`
- `Team(scope=..., policy=...)` owns agent registration, skill catalogs, workflow catalogs, and routing
- `team.add_agent(...)` is the only endorsed application construction path for runtime agents
- `Workflow(steps=[...])` routes by broad `requires_skill` domains plus optional `required_tags`; direct `agent=` pinning is an override
- Workflow routing and execution both go through Team policy checks
- Approval resumes carry structured `ProofBundle` evidence, not plain text claims
- `Workflow.code_change(...)` is a thin helper for implement/verify/review, not a replacement for dynamic workflow induction
- `ai` remains an internal engine layer, not a public package identity
- `memory` and `workspace` stay adapter-backed capabilities governed by Team policy
- `Department` / `Company` style hierarchies are optional composition layers, not mandatory core concepts
- Auth follows OAuth 2.1 / MCP gateway / A2A Agent Cards standards

The authoritative source for the full architecture - the Team-first execution
model, build order, brownfield notes, and supporting specs - is the system
vision document:

**[design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md)**

The external-review refinements that tighten standards alignment, Team-first
assembly, gateway-primary auth, structured Skills, and workspace security:

**[design/2026-06-06-review-refinements.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-review-refinements.md)**
