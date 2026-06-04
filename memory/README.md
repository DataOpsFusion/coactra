# coactra-memory

> Long-term memory for agents — across sessions and long projects — as a **thin, clean
> connector**, not a reimplemented store.

## The problem it solves

A plain LLM call reasons and shows a result but doesn't *learn*. Engines like **mem0**
and **Graphiti** already do the hard part — extraction, consolidation, recall. The real
gap is the lack of a **backend-neutral contract**: each engine has different semantics,
so you get locked in and can't A/B or move learning between them.

`coactra.memory` is that contract: a tiny, framework-agnostic facade over one async
`MemoryBackend` Protocol. It does **not** build its own vector store — it connects to the
engines that already work, and never lets an engine type leak into your code.

## Install

```bash
pip install coactra-memory                 # in-process default, zero external deps
pip install coactra-memory[mem0]           # + mem0 engine (needs an LLM + embedder)
pip install coactra-memory[graphiti]       # + Graphiti engine (needs Neo4j + an LLM)
```

## Usage

```python
from coactra.memory import Memory, make_backend, Scope, Recollection

mem = Memory(backend=make_backend("inprocess"))   # "mem0" | "graphiti" too
scope = Scope(tenant="acme", agent="builder", session=None)

# remember — the engine auto-extracts/consolidates:
await mem.remember(
    [{"role": "user", "content": "We deploy with blue-green releases."}],
    scope=scope,
)

# recall — always plain Recollection objects, never an engine type:
hits: list[Recollection] = await mem.recall("how do we deploy?", scope=scope, k=5)
for h in hits:
    print(h.score, h.text)            # (text, score, source_id, when, metadata)

# export — move a scope into another backend (LOSSY; off the headline):
await mem.export(to=make_backend("inprocess"), scope=scope)
```

### Sync bridge

For blocking callers / quick scripts, `Memory.sync` mirrors the same verbs:

```python
mem = Memory(backend=make_backend("inprocess"))
mem.sync.remember(["the build broke on the linter step"], scope=scope)
hits = mem.sync.recall("why did the build break", scope=scope)
```

(`Memory.sync.*` drives its own event loop, so call it from synchronous code — not from
inside a running loop, where you should `await` the async methods instead.)

### Shared namespaces

Use `namespace` for durable memory shared by a department, project, or company. Existing
`Scope(tenant, agent, session)` keys remain unchanged when `namespace` is omitted.

```python
agent = Scope(tenant="acme", namespace="agent", agent="builder")
department = Scope(tenant="acme", namespace="department/engineering")
company = Scope(tenant="acme", namespace="company")
```

The host decides which scopes an agent may read or publish. Wrap a memory facade with
`AuthorizedMemory` when the library should enforce those decisions before reads/writes:

```python
policy = AllowListMemoryAuthorizer()
policy.grant("agent:builder", MemoryAccess.read, department)
policy.grant("agent:builder", MemoryAccess.write, department)
mem = AuthorizedMemory(mem, actor="agent:builder", authorizer=policy)
```

Adapter authors can run `check_memory_backend_contract(backend)` in CI against real
engines so fake-only tests do not hide drift.

## Concepts

- **`Memory`** — async facade wrapping an *injected* backend (`remember` / `recall` /
  `export`), plus `Memory.sync` for blocking callers.
- **`make_backend(name, **config)`** — the DI selection point. `name` is
  `"inprocess" | "mem0" | "graphiti"`. Unknown name → `ValueError`; a known name whose
  engine extra isn't installed → `MissingExtraError`.
- **`Scope(tenant, namespace=None, agent=None, session=None)`** — the tenant-scoped
  key on every call. `namespace` adds reusable shared partitions without changing legacy
  keys. `tenant` is always encoded into the engine scope, so recall can never cross
  tenants (mem0 `user_id`/`agent_id`/`run_id`; Graphiti `group_id`).
- **`Recollection(text, score, source_id, when, metadata)`** — the only return shape. A
  mem0/Graphiti object never crosses the boundary.
- **`export()`** — lossy by design. It negotiates the source's and target's declared
  `Capability` sets and reports every dropped feature in an `ExportReport`; it never
  claims lossless conversion.

## Backends

| Backend | Engine | Notes |
|---------|--------|-------|
| `inprocess` | none | Default. Tenant-isolated dict, lexical recall, fully offline. The only backend testable with no external service. |
| `mem0` | `mem0.Memory` | Sync engine driven via `asyncio.to_thread`. Vector recall + auto-consolidation. |
| `graphiti` | `graphiti_core.Graphiti` | Native-async. Temporal knowledge graph; recalls relationship facts. |

`mem0` and `graphiti` import their engines **lazily** — importing the package never
requires the optional extras; only constructing an engine-backed backend does.

For the most portable Graphiti path, configure Coactra AI once and pass protocol
objects into the backend. LiteLLM/Instructor stay as the single model boundary, so
Claude, Qwen, DeepSeek, OpenAI-compatible endpoints, and other LiteLLM providers stay
behind one stable API.

```python
from coactra.ai import Client, LiteLLMEmbedding

backend = make_backend(
    "graphiti",
    uri="bolt://neo4j:7687",
    user="neo4j",
    password="...",
    ai_client=Client(
        model="openai/qwen3.6-plus",
        api_base="https://llm.example/v1",
        api_key="...",
    ),
    embed=LiteLLMEmbedding(
        model="openai/text-embedding-3-small",
        api_base="https://embed.example/v1",
        api_key="...",
    ),
)
```

You can still inject native Graphiti clients via `llm_client=`, `embedder=`, and
`cross_encoder=`, or configure Graphiti's built-in OpenAI-compatible clients directly
for legacy deployments. Explicitly injected native clients pass through untouched.

## Boundary

memory stores and recalls. It does **not** decide what an agent does with a memory,
does not call models itself beyond what the engine needs, and does not message agents.
The agent lib wraps `recall` into a tool; memory just answers.

See `DESIGN.md` for the locked v0.2 design.

## Silo routing

`TenantMemoryBackendRouter(factory)` selects and caches a different physical memory
backend per tenant while preserving the existing async `MemoryBackend` Protocol.
