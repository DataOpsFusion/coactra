# lib-ai ("leap AI")

> Charter only — captures the problem + vision. Full design comes later.

## The problem it solves

Common AI helper functionality gets re-implemented everywhere. There's no shared
toolkit the other libraries can all lean on — and no packaged way to **capture a
model's reasoning and replay it** instead of re-reasoning the same problem.

## The vision

A **shared library of tools / functions / classes that an AI agent can use** —
the common toolkit. Model calling, prompt building, structured output, and other
reusable capabilities live here so agents (and the other libraries) pull them off
one shelf instead of re-inventing them.

**Reasoning-replay is one of those capabilities, not the whole library** — capture
how a model reasoned through a problem so it can be reused later (feeds `orchestration.workflow`
and `memory`). It's the most novel item on the shelf, but the shelf is the point.

```python
from lib_ai import client, structured, reasoning
result = client.ask(...)                 # call any model
data   = structured(Schema, ...)         # typed output
trace  = reasoning.capture(...)          # the path it took, reusable later
```

## Wraps (swappable backends)

openai-sdk, litellm, instructor.

## Design verdict

- **Model calls + structured output → WRAP, don't build.** Solved. Use **Instructor +
  LiteLLM** (LiteLLM routes, Instructor types — LiteLLM alone won't strictly enforce
  Pydantic). Pydantic AI is the alternative if you want a fuller agent surface.
- **Reasoning capture-replay → BUILD (this is the real gap).** No packaged library does
  it. Payoff is proven (Memp: 87% vs 39%). **Guardrails are mandatory:** adaptive
  similarity gate (not static threshold), bounded quality-filtered retrieval, and a
  "replay vs re-reason" fallback — too much replay is *worse* than re-reasoning. Wrap a
  vector/procedural-memory store; the orchestration is yours.

## Open design points (later)

- Reasoning-replay boundary: does it emit a `workflow` + write to `memory`
  (producer, no own store), keep its own cache, or just memoize? (The crux.)
- The exact shared-helper surface every other library imports.

## Token budgets and silo routing

Use `count_tokens(text)` for dependency-light context estimates, or install
`coactra-ai[tiktoken]` and inject `TiktokenCounter` for tokenizer-accurate counts. Wrap
reasoning stores with `TenantReasoningStoreRouter(factory)` when each tenant needs a
separate physical vector store.
