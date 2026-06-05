# coactra-jobs

Durable work orders and reusable procedures for agent systems in one package.

- `WorkOrder` tracks one real job: assignment, leases, retries, deadlines, budgets,
  artifacts, pauses, decisions, and stable audit events.
- `Procedure` describes a reusable recipe: tasks, branches, approvals, collaboration,
  and escalation.
- `Orchestrator` links a work order to a local run-to-completion procedure runner.
- `DurableOrchestrator` links async durable-engine threads, checkpoints, approvals, and resume.

## Install

```bash
pip install coactra-jobs
pip install 'coactra-jobs[langgraph]'
pip install 'coactra-jobs[integrations]'
```

The default install remains lightweight: Pydantic plus in-memory reference stores.
LangGraph, DBOS, Temporal, Dapr, Prefect, A2A, CloudEvents, fsspec, and OpenTelemetry
integrations are optional.

## Quick Start

```python
from coactra.jobs import Orchestrator, WorkOrder, WorkScope

scope = WorkScope(tenant_id="acme", namespace="support")
orchestrator = Orchestrator()
order = orchestrator.submit(WorkOrder(scope=scope, title="Investigate INC-4821"))
```

For a simple procedure-backed run, register a `Procedure` and inject a local runner. For
production resume semantics, implement the async `WorkflowEngine.start/resume` Protocol
and inject it into `DurableOrchestrator`. Temporal and the richer homelab runtime remain
external execution targets behind that boundary.

```python
from coactra.jobs import DurableOrchestrator

orchestrator = DurableOrchestrator(engine=homelab_runtime)
result = await orchestrator.start(order.id, scope, worker="agent:builder")
```

Review before execution with plans and receipts:

```python
plan = orchestrator.work.plan(scope=scope, title="Deploy website", procedure="deploy")
receipt = orchestrator.work.execute(plan)
current = orchestrator.work.inspect(receipt)
```

`MCPTasksAdapter` exposes work orders as experimental MCP Task-shaped records. The
work ledger remains the source of truth. `InMemoryProcedurePromotionStore` adds a
review -> promote -> version -> rollback lifecycle for induced procedures.

`TenantWorkStoreRouter`, `TenantProcedureStoreRouter`, and `TenantWorkflowEngineRouter`
select a separate physical backend per tenant when hard silo isolation is required.

## Package Layout

```text
coactra.jobs            # public package root: jobs, procedures, and common adapters
coactra.jobs.workflow   # reusable procedures, handlers, stores, engines
coactra.jobs.work       # lower-level work-order ledger internals
```

The merge is packaging-level cohesion, not a forced runtime coupling. Applications may
still use either nested capability independently.

## Compatibility

The wheel keeps old import roots as thin compatibility aliases: `coactra.work`,
`coactra.workflow`, and `coactra.orchestration`. New code should import from
`coactra.jobs` or `coactra.jobs.workflow`.

Existing `coactra.jobs.*` audit event names remain stable across the package move.

## Production work ledger

Use `InMemoryWorkStore` only for tests and single-process prototypes. For durable workers,
serverless resume/checkpoint flows, or multiple worker processes, install the SQL extra and
use `SqlWorkStore`:

```bash
pip install 'coactra-jobs[sql]'
```

```python
from coactra.jobs import Scope, SqlWorkStore, WorkManager, WorkOrder

store = SqlWorkStore.from_url("sqlite:///coactra-jobs.db")
manager = WorkManager(store=store)
scope = Scope(tenant_id="acme", namespace="agent:builder")
manager.submit(WorkOrder(scope=scope, title="Build release"))
```

For production Postgres, pass a SQLAlchemy URL such as
`postgresql+psycopg://user:pass@host:5432/db`. See `../docs/jobs/WORK-ORDERS.md` for the worker
pattern and concurrency guarantees.
