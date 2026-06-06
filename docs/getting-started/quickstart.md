# Quickstart

This guide builds a small incident-response handoff. It uses the stable Coactra
facades first: `make_agent(...)` for drafting and `WorkManager` for durable work.
No subclassing, no workflow engine, no external model key.

## 1. Install

For the local agent facade:

```bash
pip install "coactra[agent]"
```

For source development:

```bash
python -m pip install -e "./coactra[all,dev]"
```

## 2. Open Durable Work

Use `WorkManager` when a task needs an id, lifecycle state, leases,
checkpoints, artifacts, or audit events.

```python
from coactra.jobs import Scope, WorkManager, WorkOrder

work = WorkManager()
scope = Scope(tenant_id="acme", namespace="incident-response")

order = work.submit(
    WorkOrder(
        scope=scope,
        title="Triage checkout latency",
        idempotency_key="incident:checkout-latency",
    )
)
```

The default store is in-memory. Replace the store with `SqlWorkStore` when work
must survive process restarts.

## 3. Draft With An Agent

```python
from coactra.agent import Scope as AgentScope, make_agent

agent = make_agent(scope=AgentScope(tenant_id="acme", namespace="agent:oncall"))
draft = agent.think("Draft the first handoff for checkout latency")
```

The default agent uses a fake local AI port. It returns a deterministic
`"completion:..."` string. Inject a real AI port for production model calls.

## 4. Finish The Handoff

```python
from coactra.jobs.work import Artifact, ArtifactPart

lease = work.claim(order.id, scope, worker="agent:oncall", lease_seconds=120)
work.start(lease, scope)
work.checkpoint(lease, scope, {"draft_handoff": draft})
completed = work.complete(
    lease,
    scope,
    artifacts=[
        Artifact(
            name="on-call-handoff",
            parts=[ArtifactPart(kind="text", text=draft)],
        )
    ],
)

print(completed.id, completed.status.value)
```

A runnable version lives at
[examples/incident_response_handoff.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/incident_response_handoff.py).
The full catalog is in [Examples](examples.md).

## 5. Production Replacements

Keep your application functions mostly the same and replace backend boundaries:

| Prototype default | Production replacement |
|---|---|
| in-memory work store | `SqlWorkStore` or another persistent `WorkStore` |
| fake AI port | real `AIPort` or integration adapter |
| in-process memory | mem0, Graphiti, or another `MemoryBackend` |
| ephemeral workspace | persistent workspace backend with explicit command policy |
| fake/local collaboration | verified A2A adapter with tenant policy |

Use `coactra.scope.CoactraScope` when one application composes several capability
roots and needs consistent tenant, namespace, agent, and session ids.
