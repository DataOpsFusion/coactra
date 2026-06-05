# State and Storage

This project has several kinds of state. Do not call something durable unless it is backed by a durable store or a host-provided runtime with persistence.

## Storage Inventory

| State | Location / owner | Default | Durable option | Notes |
|---|---|---|---|---|
| Canonical scope metadata | `coactra.scope.CoactraScope` | in memory | host-owned | Converts tenant/namespace/agent/session to package scopes. |
| AI reasoning traces | `coactra-ai` replay store | in-process dict | Chroma or custom store | Separate from long-term memory unless bridged intentionally. |
| Memory events/facts | `coactra-memory` | in-process dict | mem0 or Graphiti/Neo4j | Export is lossy; Graphiti dump is approximate. |
| Workspace files | `coactra-workspace` | local filesystem | future sandbox provider | Local backend confines paths under tenant/agent root. |
| Workspace exec output | `coactra-workspace` | subprocess result | sandbox provider | Local exec disabled by default and not a jail. |
| Work orders | `coactra-jobs` | in-memory store | `SqlWorkStore` | SQL store persists full JSON snapshot plus indexed columns. |
| Work audit events | `coactra-jobs` | in-memory events | `SqlWorkStore` events table | Used for lifecycle/audit trail. |
| Workflow approvals | `coactra-jobs` | `InMemoryApprovalStore` | host-owned or future SQL store | Clarify whether work-order pending approval is source of truth. |
| Workflow runtime checkpoint | workflow backend | backend-specific | LangGraph/Temporal/Prefect checkpointer/runtime | Coactra should wrap, not reimplement, generic checkpointing. |
| Procedure library | `ProcedureStore` | in-process store | future SQL/document store | Tenant router now forwards full store contract. |
| Organization directory | `coactra-directory` | SQLModel store | SQLite/Postgres URL | Stores tenants, departments, seats, members, reporting, escalation, grants. |
| Authorization decisions | `Authorizer` | in-memory authorizer | OpenFGA | Decisions should be auditable by host. |
| Token exchange cache | `CachedAsyncTokenExchanger` | in-process TTL dict | none | Convenience cache only; not durable auth state. |
| MCP mounted tools | `MountRegistry` | in-process pending/active trie | host/session-owned | Visible only after `begin_turn`. |

## Restart Expectations

- In-process stores lose state on restart.
- SQL work and organization stores survive restart if the database survives.
- LangGraph/Temporal/Prefect durability depends on their configured persistence.
- Workspace local files survive restart if the base directory survives.
- Token caches, mounted-tool registries, and in-memory routers are process-local.

## Recommended Production Baseline

```text
Postgres or SQLite file for work ledger
Postgres/SQLite for organization directory
Graphiti/Neo4j or mem0-backed memory when memory must persist
Keycloak token exchange for delegated identity
OpenFGA or host authorizer for external policy
LangGraph/Temporal/Prefect runtime persistence for workflow execution
Sandbox workspace backend for untrusted command execution
```

## Schema Sources

- Work SQL tables are defined in `jobs/src/coactra/jobs/work/backends/sql.py`.
- Organization SQLModel tables are defined in `directory/src/coactra/directory/models.py`.
- Workspace state is implemented by `workspace/src/coactra/workspace/backends/local.py` and `workspace/src/coactra/workspace/desk.py`.
- Memory persistence is backend-specific under `memory/src/coactra/memory/backends/`.
