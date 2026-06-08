# Agent Design

Coactra's public surface is a single `Agent` door — `from coactra import Agent`.
`Agent` is a **thin composition shell over pydantic-ai**, not a competing agent
framework. It wires memory, workspace, MCP toolsets, peer delegation, and tracing
around a pydantic-ai runtime. For direct framework access, import `pydantic_ai.Agent`
and compose with `coactra.Team` and `coactra.Workflow`.

An agent is created by naming things (model, capability names), never by
constructing ports or injecting dependencies. The old ports-based factory
composition root has been removed in the alpha redesign.

**Key principles:**

- `Agent.create(model=, tools=, memory=, workspace=, skills=, ...)` — one call, no DI
- `model=` accepts a pydantic-ai `Model` instance or a provider string (`anthropic:...`)
- Tools are unified after discovery: local functions and scoped MCP gateway tools enter the same model tool list
- `gateway=` + `auth=` is the primary MCP path; the token's scopes slice the tool list
- Memory is automatic: recall fires before the model turn; remember fires after
- `agent.card` is the curated A2A Agent Card — raw tool schemas are never advertised
- Identity (`name=`, `tenant=`) flows through the token in production
- Outbound peer delegation uses `peers=` + `CollaborationPolicy`; inbound A2A serving is host-owned via `a2a-sdk`

The authoritative spec — decisions, locked forks, built vs designed, security model,
and the cut list — is the agent API design document:

**[design/2026-06-06-agent-api-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-agent-api-design.md)**

See also the auth and identity spec for the OAuth 2.1 / OIDC / MCP gateway model:

**[design/2026-06-06-auth-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-auth-design.md)**

And the review refinements that tighten workspace security, memory guardrails,
and the structured Skill roster:

**[design/2026-06-06-review-refinements.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-review-refinements.md)**
