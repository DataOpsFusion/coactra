# workflow

> Charter only — captures the problem + vision. Full design comes later.

## The problem it solves

langgraph and temporal are fine *engines*, but you can't adjust a flow
**dynamically** — you hand-author JSON/YAML, which you don't want. And making the
agent re-reason the same path every time is a **waste of tokens**.

## The vision

Two things:

**1. Learned, self-updating flows.** The memory + reasoning layer learns the best path
**by doing it**, crafts that into a flow, and reuses it — so next time the agent
follows the known path instead of re-reasoning. Revised when reality drifts. Not
hand-written YAML.

**2. Collaboration + escalation are part of the flow.** A step can be *"go ask another
agent"* — ask a teammate, pull in another department. And when the flow can't decide on
its own, it **escalates up the `organization` hierarchy** — one tier at a time — until
a **decider** resolves it: a human (you) or, at the top, the SOTA model.
(`workflow` owns the *when/what*, `organization` routes *who/up-to-whom*, `agent`
carries the *talk*.)

```
reason once → capture the working path → becomes a flow →
reuse the flow (cheap) → update it when reality drifts
                ↑
        a step may be: ask(agent="boss") / delegate(team="...")
```

## Wraps (swappable backends)

langgraph, temporal, prefect.

## Design verdict

**BUILD a thin layer.** Hand-authored graphs are still production SOTA; learned,
self-updating flows exist only in research (AWM, NAACL 2025 — induces routines from
traces, runs online = "self-update on drift"). **Pick:** wrap a durable engine
(**LangGraph** or **Temporal**) for execution + bolt on an **AWM-style online induction
loop**. **Validate early:** is online learned control-flow cleanly bolt-on-able, or does
it force a fork of the engine? (DSPy is NOT this — don't conflate.)

## Open design points (later)

- How a reasoning trace becomes a runnable procedure (ties to `lib-ai`).
- What triggers a re-learn / update; does a human approve flow changes?

## Current Layout

```text
domain/      # procedure models and scope
runtime/     # engine protocol, run context, and handlers
backends/    # LangGraph default backend
adapters/    # optional Temporal and Prefect adapters
```

The original flat module paths remain compatibility imports.
