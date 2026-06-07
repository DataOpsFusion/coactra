# Coactra Design — Refinements from review (v2)

**Date:** 2026-06-06  **Status:** adopted. An external review + the 2026 standards confirmed **Agent / Team / Workflow** is the right public surface; these tighten the *boundaries* so the implementation is **standards-shaped, not metaphor-shaped**. Each item amends the named spec.

1. **Team stays a lean registry — not an org-chart monster.** Public name `Team`; internally it's an **agent registry/directory** (roster + capability match + who-may-talk policy). Hierarchy/escalation are optional add-ons, never the core abstraction. The industry is moving to *Agent Cards / registries / policies*, not "company simulation." *(amends team-design)*

2. **`gateway=` is the primary MCP path.** Canonical call: `Agent.create(model=, gateway="https://gateway/mcp", auth=oidc(...), tools=[local_func])`. Many `mcp(url)` objects are the exception (local/extra tools), not the norm. *(amends agent + auth)*

3. **Skills become structured (A2A-card shaped).** `skills=` accepts a curated string (simple) **or** a list of `Skill(id="cert.rotate", description="Rotate TLS certs", tags=["sre"], scopes=["cert:write"])`. Raw tool names/schemas are never exposed for discovery — "seeing ≠ calling" holds. *(amends agent + auth)*

4. **Workflow keeps an internal run-ledger model, even with a one-noun public surface.** Public: `Workflow`, `step()`. Internal: `Playbook` (definition) · `WorkflowRun` (instance) · `Step` · `Approval` · `Checkpoint`, plus a run ledger. Industry systems separate **definition vs run vs checkpoint** — we keep that distinction underneath. *(amends workflow)*

5. **Planner output is a CANDIDATE, not auto-saved.** Authored playbooks run directly; planner-generated playbooks are **candidates**, promoted into the reusable library only after **review or N successful runs**. This prevents the procedure library from self-poisoning with bad auto-generated playbooks. *(amends workflow decision ① — replaces "save for next time")*

6. **Memory guardrails — coactra owns *when/where*, the backend owns *ranking/consolidation*.** Add: tenant/user/session **scope**; **provenance** on injected memories; a **max-injected-memory** cap; a **deletion/export** path (GDPR); a **memory-write policy**. graphiti/mem0 still rank & consolidate. *(amends agent memory section)*

7. **Workspace `run` heavily gated; OWASP MCP risks are first-class.** Command exec is allow-listed by default; **tool poisoning, secret leakage, scope creep, command injection** are explicit design concerns across tools / MCP / workspace, not afterthoughts. *(amends agent workspace + the security posture)*

## Cross-cutting note
Auth/policy is **not buried inside Team or Agent** — it's the cross-cutting `auth-design.md`. Team holds the *who-may-talk policy default* (same-tenant) and points at a pluggable policy engine (OpenFGA/AuthZEN); token/scope mechanics live in auth.

## Confirmed stack alignment
MCP (tools + gateway) · OAuth 2.1/OIDC (scoped tokens) · A2A Agent Cards (discovery + advertised skills) · OpenFGA/AuthZEN (fine-grained policy) · LangGraph (agentic graph + checkpoints/interrupts) · Temporal (hard durable workflows) · Graphiti/mem0 (memory) · PydanticAI / OpenAI-Agents-style API (typed output, tools, streams, handoffs).
