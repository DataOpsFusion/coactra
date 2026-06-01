# coactra-work

Durable, tenant-scoped work orders for agent systems. A workflow describes a procedure;
a `WorkOrder` tracks one real unit of work across assignment, attempts, pauses, retries,
artifacts, decisions, and completion.

The default install is intentionally small: Pydantic plus an offline `InMemoryWorkStore`.
Production execution belongs to established runtimes through optional adapters.

## Install

```bash
pip install coactra-work
pip install 'coactra-work[dbos]'
pip install 'coactra-work[temporal]'
pip install 'coactra-work[dapr]'
pip install 'coactra-work[fsspec]'
pip install 'coactra-work[integrations]'
```

## Quick Start

```python
from coactra.work import Artifact, ArtifactPart, Scope, WorkManager, WorkOrder

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
from coactra.work.adapters import DBOSDispatcher

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
from coactra.work.adapters import TemporalDispatcher

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
The stable `coactra-work` vocabulary is suitable for a future MCP task adapter, but the
package does not freeze a pre-release Python SDK API into its public surface yet.
