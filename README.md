# Coactra

Coactra is a Python library for building AI applications that need more than one model call: durable work, memory, workspace state, organization policy, and agent-to-agent collaboration.

Install one distribution and opt into capabilities with extras:

```bash
pip install "coactra[agent]"      # agent facade (WorkManager is in the base package)
pip install "coactra[sql]"          # durable SQL work store
pip install "coactra[all,dev]"      # from source: all capability extras + pytest
```

From this repo, run the test suite with:

```bash
make test
```

## When to use Coactra

Use Coactra when you want:

- **Plain functions first** — application behavior as normal Python, with small facades for state and backends.
- **Durable work orders** — ids, lifecycle, retries, leases, audit trails, and SQL persistence via `WorkManager`.
- **Composable agent runtime** — one `make_agent(...)` facade over AI, memory, workspace, workflow, organization, and work ports.
- **Tenant-scoped isolation** — explicit `Scope` / `CoactraScope` at every boundary instead of global tenant state.
- **Swappable backends** — memory (mem0, Graphiti), workspace (local desk, future sandboxes), workflow (LangGraph, Temporal), org (SQLModel, OpenFGA).

## When not to use Coactra

Coactra is not a fit when you need:

- A batteries-included agent framework with opinionated tool loops and UI (consider PydanticAI, LangGraph apps, or similar directly).
- A general-purpose workflow engine — Coactra wraps LangGraph/Temporal/Prefect; it does not replace them.
- Production-ready defaults out of the box — reference backends (in-memory stores, `FakeAI`, local filesystem) are for development and tests.
- Stable v1 semantics today — see [Maturity](#maturity) below.

## Quick Example

```python
from coactra.agent import Scope as AgentScope, make_agent
from coactra.jobs import Scope as WorkScope, WorkManager, WorkOrder
from coactra.jobs.work import Artifact, ArtifactPart

work_scope = WorkScope(tenant_id="acme", namespace="incident-response")
agent = make_agent(scope=AgentScope(tenant_id="acme", namespace="agent:oncall"))
work = WorkManager()

order = work.submit(
    WorkOrder(scope=work_scope, title="Triage checkout latency")
)
draft = agent.think("Draft the first on-call handoff for checkout latency")

lease = work.claim(order.id, work_scope, worker="agent:oncall")
work.start(lease, work_scope)
work.checkpoint(lease, work_scope, {"draft_handoff": draft})
completed = work.complete(
    lease,
    work_scope,
    artifacts=[Artifact(name="handoff", parts=[ArtifactPart(kind="text", text=draft)])],
)

print(completed.id, completed.status.value, draft)
```

> **Default agent uses a fake model.** `make_agent(...)` with no `ai=` port wired in
> uses an in-process fake AI port that echoes the prompt. Pass a real AI port or
> integration adapter in production.

See [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) for the walkthrough, [docs/getting-started/examples.md](docs/getting-started/examples.md) for the sample catalog, and [docs/examples/incident-response-handoff.md](docs/examples/incident-response-handoff.md) for the smallest runnable app.

## Documentation

- [Docs site](docs/index.md): the public documentation entrypoint.
- [API index](docs/API_INDEX.md): stable, beta, experimental, and compatibility imports.
- [Quickstart](docs/getting-started/quickstart.md): build a small incident-triage app with plain functions.
- [Examples](docs/examples/index.md): runnable scripts and sample projects for memory, durable work, workspace, and multi-agent policy.
- [Interface map](docs/concepts/interfaces.md): package roots, stable API surfaces, and where A2A fits.
- [Production guide](docs/operations/production.md): SQL work store, scope consistency, auth, and deployment posture.
- [Library map](docs/concepts/library-map.md): capability boundaries and adapters.

## Maturity

Coactra is **alpha-quality** library infrastructure (PyPI classifier: Development Status :: Alpha). That reflects adapter maturity, default backends, and operational gaps — not permission to rename stable facades casually.

The **intended stable surface** for application code is documented in [docs/API_INDEX.md](docs/API_INDEX.md): `CoactraScope`, `Memory`, `WorkManager`, `open_workspace`, `make_agent`, and shared errors. Those facades and their Protocols should change only with changelog and migration notes until v1.

Experimental areas — `Kernel`, workflow DSL helpers, `DurableLangGraphEngine`, and most `*.adapters` modules — may change without a deprecation window. Prefer reference backends documented in [docs/operations/production.md](docs/operations/production.md) for anything beyond local prototypes.
