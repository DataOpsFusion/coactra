# Coactra

Coactra is a small set of Python libraries for building AI applications that need more than one model call: durable work, memory, workspace state, organization policy, and agent-to-agent collaboration.

The public API is meant to stay boring:

- write your application behavior as plain functions
- use `Kernel` / `Session` when you want a small beta shell around plain task functions
- use `WorkManager` when work must survive retries or restarts
- use `make_agent(...)` when you want one facade over AI, memory, workspace, workflow, organization, and collaboration
- use adapter classes only at backend boundaries, such as SQL, Keycloak, A2A, or sandbox providers

## Install

Coactra is a single distribution; pick the capabilities you need with extras:

```bash
pip install "coactra[agent]"      # agent facade (jobs/WorkManager are in the base package)
pip install "coactra[sql]"        # durable SQL work store
```

From this repo, run the test suite with:

```bash
make test
```

## Quick Example

```python
from coactra.kernel import Kernel, Task
from coactra.agent import Scope as AgentScope, make_agent
from coactra.scope import CoactraScope
from coactra.jobs import Scope as WorkScope, WorkManager, WorkOrder


def triage_incident_task(context, task):
    return {"tenant": context.scope.tenant_id, "incident": task.input["incident"]}


session = (
    Kernel.builder()
    .with_handler("triage_incident", triage_incident_task)
    .build()
    .session(CoactraScope(tenant_id="acme", namespace="support"))
)

agent_scope = AgentScope(tenant_id="acme", namespace="agent:support")
work_scope = WorkScope(tenant_id="acme", namespace="support")

agent = make_agent(scope=agent_scope)
work = WorkManager()

order = work.submit(WorkOrder(scope=work_scope, title="Triage database latency"))
result = await session.run(Task("triage_incident", {"incident": "db-latency"}))
draft = agent.think("What should we check first for database latency?")

print(order.id, order.status, result.output, draft)
```

> **The default agent uses a fake model.** `make_agent(...)` with no AI port wired in
> uses an in-process `FakeAI` that echoes the prompt — `draft` above is the literal
> string `"completion:What should we check first for database latency?"`, not real
> model output. Wire a real model (see the agent integrations / `make_coactra_agent`
> and [docs/operations/production.md](docs/operations/production.md)) to get a meaningful answer.

See [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) for a complete walkthrough, [docs/getting-started/examples.md](docs/getting-started/examples.md) for the sample catalog, and [docs/examples/basic-incident-triage.md](docs/examples/basic-incident-triage.md) for the smallest runnable app.

## Documentation

- [Docs site](docs/index.md): the public documentation entrypoint.
- [Quickstart](docs/getting-started/quickstart.md): build a small incident-triage app with plain functions.
- [Examples](docs/examples/index.md): runnable scripts and sample projects for memory, durable work, workspace, and multi-agent policy.
- [Interface map](docs/concepts/interfaces.md): package roots, stable API surfaces, and where A2A fits.
- [Production guide](docs/operations/production.md): SQL work store, scope consistency, auth, and deployment posture.
- [Library map](docs/concepts/library-map.md): package boundaries and adapters.

## Maturity

Coactra is alpha-quality library infrastructure. The core facades and Protocols are the intended stable surface. Experimental adapters are integration seams, not production backends — prefer the reference/implemented backends documented in [docs/operations/production.md](docs/operations/production.md).
