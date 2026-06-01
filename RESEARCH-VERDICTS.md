# Research Verdicts (build / wrap / don't-build)

Source: deep-research run (28 sources fetched, 134 claims extracted, 25 adversarially
verified, **24 confirmed 3-0, 1 killed**). Evidence is almost entirely primary
(arXiv papers + official docs). Current as of 2025–2026.

> **Coverage caveat (important):** the verification budget concentrated on the two
> novel cores. **Confirmed verdicts exist only for `lib-ai` (1a + 1b) and `workflow`.**
> `memory`, `workspace`, `organization`, `agent` had their sources fetched but **no
> verified claims** — they need a second pass before any verdict is trusted.

---

## lib-ai — SPLIT verdict

### (a) Multi-provider calls + structured output → **WRAP. Do not build.**
Fully solved by mature libraries.
- **Instructor** — one interface across 15+ providers (`from_provider`), typed output
  via Pydantic `response_model`. ‹python.useinstructor.com›
- **LiteLLM** — unified `response_format` JSON mode across Anthropic/OpenAI/Google/
  Vertex/Bedrock. ‹docs.litellm.ai/docs/completion/json_mode›
- **Pydantic AI** — three swappable output modes (Tool/Native/Prompted) behind one
  `output_type`. ‹ai.pydantic.dev/output›
- **Pick:** Instructor + LiteLLM (LiteLLM for routing, Instructor for the typing
  layer). **KILLED claim:** LiteLLM does *not* give strict Pydantic-direct enforcement
  uniformly — that's why you pair it with Instructor, not use it alone.

### (b) Reasoning capture-replay → **BUILD a thin layer (the real gap).**
**No packaged production library does cross-problem reasoning capture-replay.** Every
prior art is research-grade or solves an adjacent problem:
- **GPTCache** = semantic *response* cache (caches final text by input similarity) —
  does NOT capture/replay a reasoning path. Marks the boundary. ‹github.com/zilliztech/GPTCache›
- **ExpeL** (arXiv:**2308.10144**) = RAG-over-trajectories (retrieve top-k past
  successes as in-context examples), not literal replay.
- **Voyager** = executable skills as code, retrieved by embedding + *composed* — capture-then-reuse, transfers to new worlds. ‹voyager.minedojo.org›
- **Reflexion** (arXiv:2303.11366) = verbal self-reflection, only *within* a multi-trial
  loop on the **same** task — not cross-problem.
- **Memp** (arXiv:2508.06433, ACL 2026) = distills trajectories into procedural memory,
  replays on analogous tasks.
- **DSPy** = NEGATIVE reference — tunes prompts/weights against a metric (compile-time),
  not per-problem replay. Don't conflate. ‹dspy.ai/learn/optimization/optimizers›

**Payoff is REAL, not hypothetical:** Memp on ALFWorld w/ GPT-4o hit **87.14% success
in 15.01 steps vs 39.28% in 23.76 steps** no-memory — accuracy up *and* cost down.

**Build guardrails (mandatory — these are documented failure modes):**
1. **Reuse is non-monotonic.** Retrieving too many memories DEGRADES performance
   (context bloat + interference). → **bounded, quality-filtered retrieval**, tuned count.
2. **Static similarity thresholds have no correctness guarantee** (unpredictable error
   rates). → use an **adaptive/verified gate** (à la **vCache**, arXiv:2502.03771 —
   up-to 12.5× hit rate, 26× lower error vs static).
3. **Need a "replay vs re-reason" decision rule** — past a point, replay is *worse* than
   re-reasoning. The thin layer must know when to fall back.
- **What to wrap:** FAISS/vector store + a procedural-memory store. **What's novel
  (yours to own):** the capture→gate→bounded-retrieve→replay-or-fallback orchestration.

---

## workflow — **BUILD a thin layer (learned/self-updating is unfilled).**
Hand-authored workflow graphs are still **production SOTA**. Learned, self-updating
flows exist **only in research**:
- **AWM** (Agent Workflow Memory, arXiv:2409.07429, NAACL 2025) — induces reusable
  routines from past trajectories, injects them into context. Runs **offline AND
  online** (induce from test queries on the fly) = the "self-update when reality drifts"
  property. But it's a method, not an engine.
- **ADAS** ‹github.com/ShengranHu/ADAS› — automated agent design (research).
- **Engines to wrap for durable execution:** LangGraph / Temporal / Prefect /
  **Burr** ‹github.com/DAGWorks-Inc/burr›.
- **Pick:** wrap a durable engine (LangGraph or Temporal) + bolt on an **AWM-style
  online induction loop**. **Open risk:** is online learned control-flow cleanly
  thin-wrappable, or does it force a fork of the engine? Validate early.

---

## memory / workspace / organization / agent — SECOND-PASS VERDICTS (verified 2026-06-01 vs primary sources)

An external (GPT/Codex) review proposed these; its load-bearing post-cutoff claims were
**checked directly against primary sources and confirmed.**

- **memory → WRAP + thin connector SPI.** Engines already consolidate from conversations
  — LangMem (extract/consolidate/update), Letta (self-edited memory blocks), Mem0,
  Graphiti. Don't replace them. Build a backend-neutral contract; **`export()` is lossy**
  (graph vs vector vs block semantics) → capability negotiation + provenance + explicit
  unsupported-feature reports. ‹langchain-ai.github.io/langmem›, ‹docs.letta.com›,
  ‹docs.mem0.ai›, ‹github.com/getzep/graphiti›
- **workspace → BUILD thin control layer over persistent sandboxes.** Field is NOT empty:
  Daytona (persistent sandboxes + snapshots + lifecycle + MCP), E2B (pause/resume fs +
  process), OpenHands (persists convo + MCP + tools + agent state), Docker volumes. None
  package the "agent desk" (files + CLI policy + handoff + capability manifest). Build
  that above them. ‹daytona.io/docs›, ‹e2b.dev/docs/sandbox/persistence›, ‹docs.openhands.dev›
- **organization → BUILD thin standalone directory.** CrewAI hierarchical process +
  LangGraph Supervisor exist but bake org into *execution*. Standalone multi-tenant
  directory (tenants, departments, roles/seats, memberships, reporting, escalation,
  policy refs) is a real gap. **No workflow execution inside it.**
  ‹docs.crewai.com/en/learn/hierarchical-process›, ‹github.com/langchain-ai/langgraph-supervisor-py›
- **agent → WRAP protocols + BUILD composition/policy layer.** VERIFIED against primary
  sources: A2A is mature (v1.0.1, 2026-05-28 — tasks/multi-turn/streaming/push/artifacts);
  MCP `2025-11-25` negotiates `tools.listChanged`; FastMCP mounting is a *live* link;
  OpenAI Agents SDK re-lists per run + `invalidate_tools_cache()`; MCP OAuth supports
  on-behalf-of but **forbids token passthrough** (use RFC 8693). Don't fork the protocols.
  Gap = session-level orchestration (mid-session mount → next-safe-turn exposure,
  conflict/cache handling) + delegated identity. ‹github.com/a2aproject/A2A/releases›,
  ‹modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle›,
  ‹modelcontextprotocol.io/specification/2025-11-25/basic/authorization›,
  ‹gofastmcp.com/servers/composition›, ‹openai.github.io/openai-agents-python/mcp›,
  ‹rfc-editor.org/info/rfc8693›

**Overarching principle (confirmed):** these libraries should CONNECT existing systems
through small contracts — not compete with memory engines, sandbox providers, MCP, or A2A.

## Open questions to resolve before building
- 1b: which primitive to wrap — procedural-memory store (Memp) vs trajectory-RAG
  (ExpeL/Voyager) vs verified semantic cache (vCache)? Do "same problem" vs "analogous
  task" vs "reusable skill" need different stores?
- 1b: can the two failure-mode guards (adaptive gate + bounded retrieval + re-reason
  fallback) be one unified guard?
- workflow: is the AWM online loop bolt-on-able to LangGraph/Temporal, or fork-forcing?
