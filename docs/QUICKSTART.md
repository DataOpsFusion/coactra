# Quickstart

This guide builds a small incident-triage agent. It is intentionally function-first: the app behavior is written as plain functions, and Coactra classes appear only where they hold state or define a backend boundary.

## 1. Install

For a local prototype (jobs/`WorkManager` are in the base package):

```bash
pip install "coactra[agent]"
```

For durable work in a real service:

```bash
pip install "coactra[sql]"
```

For source development, install the local checkout in editable mode:

```bash
python -m pip install -e "./coactra[all,dev]"
```

## 2. Start With A Task Function

Most application code should look like normal Python. Do not start by designing subclasses.

```python
def summarize_incident(agent, incident: str) -> str:
    return agent.think(f"Summarize the incident and name the first check: {incident}")
```

The `agent` argument can be a Coactra `Agent`, a test fake, or any object with the small methods this function needs.

## 3. Add Durable Work

Use `WorkManager` when a task needs an id, lifecycle state, retries, leases, audit events, or persistence.

```python
from coactra.jobs import Scope, WorkManager, WorkOrder

work = WorkManager()
scope = Scope(tenant_id="acme", namespace="support")

order = work.submit(
    WorkOrder(
        scope=scope,
        title="Triage database latency",
        idempotency_key="incident:db-latency-001",
    )
)
```

`WorkManager` is a class because it owns state through a `WorkStore`. Your application behavior around it can remain functions.

## 4. Add The Agent Facade

Use `make_agent(...)` when you want one object that delegates to AI, memory, workspace, workflow, organization, durable work, identity, and collaboration ports.

```python
from coactra.agent import Scope as AgentScope, make_agent

agent = make_agent(scope=AgentScope(tenant_id="acme", namespace="agent:support"))
answer = agent.think("What should we check first for database latency?")
```

The default agent is dependency-light and uses in-process defaults — including an in-process `FakeAI` that **echoes the prompt** (`agent.think("...")` returns `"completion:..."`, not real model output). Wire a real AI client to get real answers; swap other ports only when you need real backends.

## 5. Compose A Small App

```python
import hashlib

from coactra.agent import Scope as AgentScope, make_agent
from coactra.jobs import Scope as WorkScope, WorkManager, WorkOrder


def incident_key(incident: str) -> str:
    digest = hashlib.sha256(incident.encode("utf-8")).hexdigest()[:16]
    return f"incident:{digest}"


def submit_incident(work: WorkManager, scope: WorkScope, incident: str) -> WorkOrder:
    return work.submit(
        WorkOrder(
            scope=scope,
            title=f"Triage incident: {incident[:60]}",
            idempotency_key=incident_key(incident),
        )
    )


def triage_incident(incident: str) -> dict[str, str]:
    agent = make_agent(scope=AgentScope(tenant_id="acme", namespace="agent:support"))
    work = WorkManager()
    work_scope = WorkScope(tenant_id="acme", namespace="support")

    order = submit_incident(work, work_scope, incident)
    draft = agent.think(f"Give the first three checks for: {incident}")

    return {"work_id": order.id, "status": order.status.value, "draft": draft}
```

A runnable version lives at [https://github.com/DataOpsFusion/coactra/blob/main/examples/basic_incident_triage.py](https://github.com/DataOpsFusion/coactra/blob/main/examples/basic_incident_triage.py). More complete sample projects are listed in [EXAMPLES.md](EXAMPLES.md).

## 6. Move From Prototype To Production

Replace only the backend boundary. The application functions do not need to change.

```python
from coactra.jobs import SqlWorkStore, WorkManager

store = SqlWorkStore.from_url("postgresql+psycopg://coactra:secret@db/coactra")
work = WorkManager(store=store)
```

For composed apps, use `coactra.scope.CoactraScope` to keep tenant, namespace, agent, and session ids consistent across packages.

## 7. Where A2A Fits

A2A is for service-to-service agent communication. You do not need it for a local app with one agent.

Use A2A when:

- one agent service must ask another agent service for help
- the receiving service exposes an official A2A endpoint
- you need auth, audience, and tenant policy before messages hit the wire

Coactra keeps A2A at adapter edges:

- `coactra.agent` owns the collaboration policy and transport Protocols
- `coactra.agent.adapters` owns the official A2A SDK client/server helpers
- `coactra.jobs.adapters` converts skills and artifacts into A2A shapes

## 8. When To Use Classes

Use a class when it owns one of these:

- durable state, such as `WorkManager` or `SqlWorkStore`
- a backend boundary, such as an A2A transport or Keycloak exchanger
- a long-lived facade, such as `Agent`, `Memory`, or `Workspace`

Use functions for business behavior:

- `triage_incident(...)`
- `submit_release_work(...)`
- `summarize_customer_thread(...)`
- `choose_next_check(...)`

That is the intended style. Coactra should give you stable seams, not force you into a subclass tree.
