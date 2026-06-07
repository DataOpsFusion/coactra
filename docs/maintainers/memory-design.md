# Memory Design

Memory is an **agent capability**, not a standalone domain. You enable it with
`Agent.create(memory="graphiti")` — the agent auto-recalls before each model turn
and auto-stores the turn after. coactra is a pure connector: it calls the backend's
own `recall()` / `remember()` APIs and never ranks, stores, or judges salience itself.

**Key principles:**

- Named capability: `memory="graphiti"` / `"mem0"` / `"inprocess"` (dev)
- Automatic: recall fires before the model sees the user message; remember fires after
- coactra owns *when/where* (scope, provenance, cap); the backend owns *ranking/consolidation*
- Memory scope is isolated per tenant automatically
- Memory guardrails: tenant/session scope, injected-memory cap, deletion/export path (GDPR)
- Backends: Graphiti (Neo4j + LLM, relational facts), mem0 (OSS / cloud), inprocess (ephemeral dev)

The authoritative spec for memory — automatic connector model, guardrails, scope,
provenance, and backend wiring — lives in the agent API design document (memory
section):

**[design/2026-06-06-agent-api-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-agent-api-design.md)**

The memory guardrail decisions (scope, cap, deletion, write policy) are captured in
the review refinements:

**[design/2026-06-06-review-refinements.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-review-refinements.md)**
