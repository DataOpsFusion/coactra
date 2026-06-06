# coactra.jobs work orders

Durable, tenant-scoped work orders for agent systems. A workflow describes a procedure;
a `WorkOrder` tracks one real unit of work across assignment, attempts, pauses, retries,
artifacts, decisions, and completion.

The default install is intentionally small: Pydantic plus an offline `InMemoryWorkStore`.
Production execution belongs to established runtimes through optional adapters.

## Install

```bash
pip install coactra
pip install 'coactra[sql]'
pip install 'coactra[dbos]'
pip install 'coactra[temporal]'
pip install 'coactra[dapr]'
pip install 'coactra[fsspec]'
pip install 'coactra[integrations]'
```

## Quick Start

```python
from coactra.jobs import Artifact, ArtifactPart, Scope, WorkManager, WorkOrder

scope = Scope(tenant_id="acme", namespace="support")
work = WorkManager()
order = work.submit(WorkOrder(scope=scope, title="Prepare incident report"))
lease = work.claim(order.id, scope, worker="agent:analyst")
work.start(lease, scope)
work.complete(
    lease,
    scope,
    artifacts=[Artifact(name="report", parts=[ArtifactPart(kind="text", text="done")])],
)
```

## What Coactra Owns

Coactra owns the stable cross-runtime vocabulary and the offline reference behavior:

- `WorkOrder`, `WorkStatus`, `Attempt`, `Lease`, `RetryPolicy`, `Deadline`
- `Checkpoint`, `ResumeToken`, `ApprovalRequest`, `ElicitationRequest`, `Decision`
- `Artifact`, `ArtifactPart`, `ArtifactRef`, `Provenance`
- `AgentSpec`, `SkillSpec`, `CapabilityDescriptor`, `CapabilityRequirement`
- `EventEnvelope`, `WorkStore`, `AuditSink`, `WorkManager`

It does not attempt to become a message broker, scheduler, or workflow engine.

## Runtime Adapters

| Extra | Adapter | Use it when |
|---|---|---|
| `dbos` | `DBOSDispatcher` | You want lightweight durable queues, retries, recovery, scheduling, and notifications backed by SQLite or Postgres. |
| `temporal` | `TemporalDispatcher` | You want Temporal's server-backed workflow history, workers, signals, activities, and operational model. |
| `dapr` | `DaprDispatcher` | You want CNCF-backed Dapr Workflow with sidecar state stores and service-oriented workflow APIs. |
| `fsspec` | `FsspecArtifactStore` | You want artifact envelopes on local filesystems, S3, GCS, or another fsspec-compatible store. |
| `a2a` | `to_a2a_agent_card`, `to_a2a_artifact` | You expose agent skills and task artifacts through the official A2A SDK. |
| `cloudevents` | `to_cloudevent` | You publish audit transitions through the CNCF CloudEvents format. |
| `otel` | `OpenTelemetryAuditSink` | You export lifecycle telemetry through the OpenTelemetry API. The application chooses its SDK and exporter. |

Example DBOS submission:

```python
from coactra.jobs.adapters import DBOSDispatcher

dispatcher = DBOSDispatcher.connect(
    system_database_url="postgresql://localhost/app",
    workflow_name="jobs.process_work",
    queue_name="agent-work",
    partition_by_scope=True,
)
external_id = dispatcher.submit(order)
```

Example Temporal submission:

```python
from coactra.jobs.adapters import TemporalDispatcher

dispatcher = await TemporalDispatcher.connect(
    "localhost:7233",
    workflow=RunWork.run,
    task_queue="agent-work",
)
handle = await dispatcher.submit(order)
```

## Protocol Notes

A2A already standardizes agent cards, skills, tasks, lifecycle states, and artifacts, so
Coactra converts into the official SDK rather than forking the wire protocol.

MCP tasks were introduced in specification version `2025-11-25` and remain experimental.
The stable `coactra.jobs` vocabulary is suitable for a future MCP task adapter, but the
package does not freeze a pre-release Python SDK API into its public surface yet.

## Durable SQL WorkStore

`InMemoryWorkStore` is the dependency-light reference backend. Use it for unit tests,
examples, and single-process prototypes only. It is not a production ledger because state is
process-local and does not survive restart.

For backend services, long-running workers, serverless resume/checkpoint flows, and
multi-process execution, use `SqlWorkStore`:

```python
from coactra.jobs import Scope, SqlWorkStore, WorkManager, WorkOrder

store = SqlWorkStore.from_url("sqlite:///coactra-jobs.db")
manager = WorkManager(store=store)
scope = Scope(tenant_id="acme", namespace="agent:builder")

order = manager.submit(WorkOrder(scope=scope, title="Build release"))
lease = manager.claim(order.id, scope, worker="worker-1", lease_seconds=300)
manager.start(lease, scope)
manager.checkpoint(lease, scope, {"step": "compiled"})
```

### Local SQLite example

Install the SQL extra, then use a file-backed SQLite database:

```bash
pip install 'coactra[sql]'
```

```python
store = SqlWorkStore.from_url("sqlite:///./coactra-jobs.db")
manager = WorkManager(store=store)
```

SQLite is appropriate for local development, smoke tests, and small single-host workers. For
multiple hosts or high write concurrency, use Postgres.

### Postgres production example

`SqlWorkStore` accepts any SQLAlchemy URL. For Postgres, install a driver such as psycopg and
use a Postgres URL:

```bash
pip install 'coactra[sql]' psycopg[binary]
```

```python
store = SqlWorkStore.from_url(
    "postgresql+psycopg://coactra:secret@postgres.internal:5432/coactra"
)
manager = WorkManager(store=store)
```

The store persists the complete `WorkOrder` snapshot as JSON, including attempts, leases,
checkpoints, pending approval/input/auth requests, decisions, budgets, artifacts, status, and
audit context. Indexed SQL columns store `tenant_id`, `namespace`, `status`,
`idempotency_key`, and `version` for scoped lookup and optimistic concurrency.

### Worker setup pattern

Each worker process should construct its own SQLAlchemy-backed `SqlWorkStore` and
`WorkManager`:

```python
store = SqlWorkStore.from_url(os.environ["COACTRA_WORK_DATABASE_URL"])
manager = WorkManager(store=store)

order = manager.get(work_id, scope)
lease = manager.claim(order.id, scope, worker=os.environ["WORKER_ID"])
manager.start(lease, scope)
try:
    # do work
    manager.complete(lease, scope)
except Exception as exc:
    manager.fail(lease, scope, error=str(exc), retry=True)
```

`save(..., expected_version=...)` uses an atomic SQL `UPDATE ... WHERE version = ...`, so a
stale worker cannot overwrite a newer lease, checkpoint, approval, or completion state. If a
worker observes a `ConflictError` or `LeaseError`, it should reload the work order and decide
whether to back off, retry later, or abandon the claim.
