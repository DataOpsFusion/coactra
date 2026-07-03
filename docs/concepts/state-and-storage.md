# State and Storage

This project has several kinds of state. Do not call something durable unless it
is backed by a durable store or a host-provided runtime with persistence.

## Storage Inventory

| State | Location / owner | Default | Durable option | Notes |
|---|---|---|---|---|
| Canonical scope metadata | `coactra.Scope` | in memory | host-owned | Converts tenant/namespace/agent/session to package scopes. |
| Memory events/facts | `coactra[memory]` | in-process dict | mem0, Graphiti/Neo4j, or host-owned recall source | Export is optional and lossy. |
| Workspace files | `coactra[workspace]` | local filesystem | future sandbox provider | Local backend confines paths under tenant/agent root. |
| Workspace exec output | `coactra[workspace]` | subprocess result | sandbox provider | Local exec disabled by default and not a jail. |
| Work orders | `coactra[workflow]` | in-memory store | `SqlWorkStore` | SQL store persists full JSON snapshot plus indexed columns. |
| Work audit events | `coactra[workflow]` | in-memory events | `SqlWorkStore` events table | Used for lifecycle/audit trail. |
| Workflow approvals | `coactra[workflow]` | `InMemoryApprovalStore` | host-owned or future SQL store | Clarify whether work-order pending approval is source of truth. |
| Procedure runtime state | `WorkflowEngine` | in-process engine state | host runtime or custom engine | The default engine resumes inside one process; inject Temporal/Prefect/custom for hard durability. |
| Procedure library | `ProcedureStore` | in-process store | future SQL/document store | Tenant router forwards full store contract. |
| Team directory | `coactra[team]` | SQLModel store | SQLite/Postgres URL | Stores tenants, departments, seats, members, reporting, escalation, grants. |
| Authorization decisions | `Authorizer` | in-memory authorizer | OpenFGA | Decisions should be auditable by host. |
| Token exchange cache | `CachedAsyncTokenExchanger` | in-process TTL dict | none | Convenience cache only; not durable auth state. |
| MCP mounted tools | `MountRegistry` | in-process pending/active trie | host/session-owned | Visible only after `begin_turn`. |

## Restart Expectations

- In-process stores lose state on restart.
- SQL work and team stores survive restart if the database survives.
- The local durable workflow adapter can pause/resume inside the same process; process-restart durability requires an injected host runtime or store-backed engine.
- Temporal/Prefect/custom runtime durability depends on their configured persistence.
- Workspace local files survive restart if the base directory survives.
- Token caches, mounted-tool registries, and in-memory routers are process-local.

## Recommended Production Baseline

```text
Postgres or SQLite file for work ledger
Postgres/SQLite for team directory
Graphiti/Neo4j or mem0-backed memory when memory must persist
Keycloak token exchange for delegated identity
OpenFGA or host authorizer for external policy
Temporal/Prefect/custom WorkflowEngine for process-restart workflow execution
Sandbox workspace backend for untrusted command execution
```

## Schema Sources

- Work SQL tables are defined in `coactra/src/coactra/workflow/ledger/backends/sql.py`.
- Organization SQLModel tables are defined in `coactra/src/coactra/team/directory/models.py`.
- Workspace state is implemented by `coactra/src/coactra/workspace/backends/local.py` and `coactra/src/coactra/workspace/desk.py`.
- Memory persistence belongs to the supplied source; Coactra only requires `recall()`.
