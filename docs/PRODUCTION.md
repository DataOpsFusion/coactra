# Production Deployment Guide

This guide describes the minimum production posture for Coactra applications.

## Recommended package posture

Use stable package roots for application code and keep experimental adapters behind explicit imports and configuration.

> **Pre-release:** the `coactra-*` distributions are not on PyPI yet — install them
> editable from the monorepo today (see [../CONTRIBUTING.md](../CONTRIBUTING.md)). Pin
> versions and extras in your deployment lockfile once they are published.

```bash
pip install "coactra-jobs[sql]" coactra-agent coactra-workspace coactra-memory
```

Use package-specific extras only where required:

```bash
pip install "coactra-agent[oauth]"        # Keycloak/OAuth token exchange with httpx
pip install "coactra-jobs[sql]"  # SQLAlchemy-backed durable WorkStore
```

## Durable work execution

Use `SqlWorkStore` for backend services, long-running workers, serverless resume flows, or any deployment with more than one process. `InMemoryWorkStore` is only suitable for unit tests, demos, and single-process prototypes.

SQLite is useful for local development:

```python
from coactra.jobs import Scope, SqlWorkStore, WorkManager, WorkOrder

store = SqlWorkStore.from_url("sqlite:///./coactra-jobs.db")
manager = WorkManager(store)
scope = Scope(tenant_id="tenant-a", namespace="prod")
```

Postgres-compatible deployments should use a SQLAlchemy URL and run the same store API:

```python
from coactra.jobs import SqlWorkStore

store = SqlWorkStore.from_url(
    "postgresql+psycopg://coactra:${COACTRA_DB_PASSWORD}@db.internal:5432/coactra"
)
```

The SQL store provides optimistic version checks and atomic claim updates. Workers should always claim work before executing it and save checkpoints after externally visible progress.

```python
order = manager.submit(
    WorkOrder(scope=scope, title="sync account", metadata={"account_id": "acct_123"})
)
lease = manager.claim(order.id, scope, worker="worker-1", lease_seconds=300)

try:
    manager.start(lease, scope)
    manager.checkpoint(lease, scope, {"phase": "started"})
    # execute durable step here
    manager.complete(lease, scope)
except Exception as exc:
    manager.fail(lease, scope, error=str(exc), retry=True)
    raise
```

## Scope consistency

Use `coactra.scope.CoactraScope` when one application composes multiple packages. It documents the conversion rules and prevents tenant, namespace, agent, and session collisions.

```python
from coactra.scope import CoactraScope

scope = CoactraScope(
    tenant_id="tenant-a",
    namespace="support",
    agent_id="triage-agent",
    session_id="session-1",
)

agent_scope_kwargs = scope.to_agent_kwargs()
work_scope_kwargs = scope.to_work_kwargs()
workspace_scope_kwargs = scope.to_workspace_kwargs()
memory_scope_kwargs = scope.to_memory_kwargs()
```

## Workspace execution policy

Local subprocess execution is unsafe for untrusted users. In production, prefer sandboxed or remote workspace backends. If local execution is enabled, pass an explicit policy, timeout, output cap, cwd, and environment allowlist.

Do not enable broad shell execution for user-provided commands.

## Auth and secrets

Use `AsyncKeycloakExchanger` or a cached async exchanger in async services. Avoid blocking token exchange in request handlers. Keep client secrets in the platform secret manager and never store tokens in work payloads or event metadata.

## Adapter posture

Treat experimental adapters (e.g. the DBOS/Temporal/Dapr dispatch bridges) as integration seams, not production backends. Prefer the reference/implemented backends: `SqlWorkStore` over `InMemoryWorkStore`, sandboxed or remote workspaces over local exec, a persistent-checkpointer `DurableLangGraphEngine` with an explicit restart contract, and real token exchange over the in-process exchanger.

## Deployment checklist

- Use `SqlWorkStore` for durable workflows.
- Configure database backups and retention for work-order tables.
- Use explicit tenant and namespace values for every request path.
- Use `CoactraScope` in composed apps to avoid scope-field drift.
- Disable local exec unless the worker is isolated and trusted.
- Set workspace exec timeouts and output limits.
- Use async token exchange in async services.
- Avoid storing secrets in payloads, checkpoints, approvals, or metadata.
- Pin package versions and extras in your deployment lockfile.
- Run the package test suite for every adapter you enable.


## Capability registry and verification

For production workflows that call tools, register capabilities up front and pass the registry into `DurableLangGraphEngine`. The registry validates that tool nodes reference real tools and that required inputs are present before execution.

Use structured done criteria such as `success`, `not_error`, `equals`, and `cel` instead of checking only that a key exists. `run_workflow` records `_verification` with status, failures, and evidence.
