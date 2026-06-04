# coactra.memory — v0.2 (clean facade + real mem0/graphiti adapters)

> The point: give an agent **long-term memory across sessions/long projects**. mem0 and
> Graphiti ALREADY do extraction+consolidation+recall — so memory is a **thin, clean
> connector**, not a reimplemented store. The value is (1) a tiny, framework-agnostic
> public API that a2a/openai-sdk/the agent lib can wrap in a few lines, and (2) two REAL
> adapters behind one Protocol so you can A/B engines. We do NOT build our own vector DSA.

## Locked decisions
- **Async-first facade + thin sync wrapper.** Core is `await`; `Memory.sync` bridges for
  blocking callers. (mem0 is sync → run in a threadpool; Graphiti is native async.)
- **Two verbs on the headline surface:** `remember`, `recall`. `export` stays but moves
  OFF the headline (explicit `mem.export(to=...)`).
- **No engine types leak.** Returns are plain `Recollection`. `Scope` is a value object.
- **DI + factory.** Backend is injected; `make_backend(name, **config)` selects it.

## Public API (the clean, wrappable surface)
```python
from coactra.memory import Memory, make_backend, Scope, Recollection

mem = Memory(backend=make_backend("mem0"))        # "graphiti" | "inprocess" too
scope = Scope(tenant="acme", agent="builder", session=None)

await mem.remember(conversation, scope=scope)     # engine auto-extracts/consolidates
hits: list[Recollection] = await mem.recall("deploy decisions?", scope=scope, k=5)
await mem.export(to=other_backend, scope=scope)    # lossy; off the headline

# sync bridge for blocking callers / quick scripts:
Memory(backend=make_backend("inprocess")).sync.recall("q", scope=scope)
```
- `Recollection` = `(text: str, score: float, source_id: str, when: datetime|None, metadata: dict)` — a plain dataclass/pydantic model. NEVER a mem0/graphiti object.
- `Scope` = `(tenant: str, namespace: str|None, agent: str|None, session: str|None)`.
  Existing three-slot keys remain stable when `namespace` is omitted. Namespaced scopes
  use a distinct discriminator and map to mem0 `user_id`/`agent_id`/`run_id` filters or
  Graphiti `group_id`. Tenant isolation is always enforced.

## Layers
```
facade.py        # Memory (async) + Memory.sync ; wraps an injected MemoryBackend
types.py         # Scope, Recollection, MemoryEvent — plain, framework-agnostic
backends/
  base.py        # MemoryBackend Protocol (async): remember/recall/export/capabilities
  inprocess.py   # default: simple lexical/dedup store — tests & offline, no DSA pretense
  mem0.py        # Mem0Backend — wraps mem0.Memory (sync → threadpool); add()/search()
  graphiti.py    # GraphitiBackend — wraps graphiti_core.Graphiti (async); add_episode()/search()
factory.py       # make_backend(name, **config) -> MemoryBackend
export.py        # lossy capability negotiation (kept from v0.1, off headline)
```

## MemoryBackend Protocol (async)
```python
class MemoryBackend(Protocol):
    async def remember(self, events: list[MemoryEvent], scope: Scope) -> None: ...
    async def recall(self, query: str, scope: Scope, k: int = 10) -> list[Recollection]: ...
    async def capabilities(self) -> set[Capability]: ...
    async def dump(self, scope: Scope) -> list[Recollection]: ...   # for export
    async def ingest(self, items, scope: Scope) -> "ExportReport": ...
```

## Adapters — what's real vs mocked
- **Mem0Backend**: `remember` → `Memory.add(messages, user_id=…)` in a threadpool; `recall`
  → `Memory.search(query, filters=…, top_k=k)` → map results to `Recollection`. Config via
  `make_backend("mem0", config={...})` (LLM/embedder/vector-store; OSS via Ollama).
- **GraphitiBackend**: `remember` → `await g.add_episode(..., group_id=…)`; `recall` →
  `await g.search(query, group_id=…)` → map to `Recollection`. Needs Neo4j+LLM. It
  accepts injected native clients or explicit OpenAI-compatible LLM/embedder settings;
  `llm_provider="openai_generic"` selects Graphiti's portable chat-completions client.
- **Testing**: in-process backend fully unit-tested; mem0/graphiti adapters unit-tested
  with MOCKED engine clients (assert correct engine calls + scope mapping + Recollection
  mapping, no type leak); live integration tests gated behind env (mem0/OPENAI, NEO4J) and
  skipped otherwise. Async tests via asyncio. Never fake green.

## Boundary
memory stores/recalls. It does NOT decide what an agent does with a memory, does not call
models itself beyond what the engine needs, does not message agents. The agent lib wraps
`recall` into a tool; memory just answers.
