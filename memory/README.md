# memory

> Charter only — captures the problem + vision. Full design comes later.

## The problem it solves

A plain LLM call reasons and shows a result but doesn't *learn* — a human walks away
from a conversation having learned (lessons, patterns, preferences). **Correction:**
"agents are always stateless" is too strong — engines already consolidate this (LangMem
extract/consolidate/update, Letta self-edited memory blocks, Mem0, Graphiti). The real
gap is **no backend-neutral contract**: each engine has different semantics, so you get
locked in and can't move learning between them.

## The vision

A **learning** layer, not just a store. It **learns in-memory** during a session
(consolidates what mattered, the way a human does after a conversation), and can then
**extract / export that learning into any RAG or memory backend** — graphiti, mem0,
vector DB, whatever. The in-memory learning is the universal part; the backend is
swappable.

```python
agent.memory("Write down the result")     # write, that easy
agent.recall("what was the result?")       # comes back next session
mem.flush(to=my_rag_backend)               # export learning to any system
```

## Wraps (swappable backends)

mem0, graphiti/zep, letta, llama-index, qdrant, neo4j.

## Verdict (from research — see ../RESEARCH-VERDICTS.md)

**WRAP + thin connector SPI. Do NOT replace the engines** — they already consolidate
from conversations. Build a backend-neutral contract: `learn(events, scope)` /
`recall(query, capabilities=...)` / `export(to=adapter)`. **Critical: `export()` is
lossy** — graph vs vector vs Letta-block semantics differ — so use capability
negotiation, provenance, and explicit unsupported-feature reports. Never promise
lossless conversion.

## Open design points (later)

- What's a "fact" vs a raw blob? How is it ranked / retrieved?
- Scope: per-agent, per-session, shared?
- **Distinct from `lib-ai` reasoning-capture** (decided): `memory` learns from the
  *conversation* (summaries, lessons); `lib-ai` captures the *model's own reasoning*.
  Different source, no shared store.
