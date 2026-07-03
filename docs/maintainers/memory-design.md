# Memory Design

Memory is a **connector capability**, not a standalone memory framework. You enable it through
`team.add_agent(memory=..., model_capability=...)`. The minimum contract is
`recall(query, scope, k)`. If the source also supports `remember(events, scope)`,
the agent can auto-store after a turn. Coactra is a pure connector: it calls the
source's own APIs and never ranks, stores, or judges salience itself.

**Key principles:**

- Named capability: `memory="graphiti"` / `"mem0"` / `"inprocess"` (dev)
- Existing source: pass an object with `recall()` or a plain recall callable
- Automatic: recall fires before the model sees the user message; remember fires after only when supported
- coactra owns *when/where* (scope, provenance, cap); the memory source owns *ranking/consolidation*
- Memory scope is isolated per Team scope automatically
- Memory guardrails: tenant/session scope, injected-memory cap, deletion/export path (GDPR)
- Sources: Graphiti (Neo4j + LLM, relational facts), mem0 (OSS / cloud), inprocess (ephemeral dev), or host-owned search/RAG
- Team-owned model routes can point at live OpenCode/Zen profiles or deterministic local models without changing the memory contract

The authoritative spec for memory — automatic connector model, guardrails, scope,
provenance, and backend wiring — lives in the agent API design document (memory
section):

**[design/2026-06-06-agent-api-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-agent-api-design.md)**

The memory guardrail decisions (scope, cap, deletion, write policy) are captured in
the review refinements:

**[design/2026-06-06-review-refinements.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-review-refinements.md)**
