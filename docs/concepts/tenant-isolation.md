# Tenant Isolation

Tenant isolation is a design constraint across the library. Every package should receive an explicit scope or tenant-qualified reference rather than inferring tenancy from global state.

## Scope Shapes

| Package | Scope shape | Purpose |
|---|---|---|
| `coactra` | `Scope(tenant_id, namespace, agent_id, session_id)` | Canonical DTO and conversion helper. |
| `coactra[agent]` | `Scope(tenant_id, namespace)` | Agent runtime and collaboration policy scope. |
| `coactra[memory]` | `Scope(tenant, namespace, agent, session)` | Memory partitioning across tenant/shared/agent/session levels. |
| `coactra[workspace]` | `Scope(tenant_id, agent_id)` | Path-safe filesystem/sandbox root. |
| `coactra[workflow]` | `Scope(tenant_id, namespace)` | Procedure and workflow runtime partition. |
| `coactra[workflow]` | `WorkScope(tenant_id, namespace)` | Durable work ledger partition. |
| `coactra[team]` | tenant on root/org/store operations | Tenant is the team directory isolation boundary. |

## Isolation Mechanisms

- Memory encodes tenant into backend-specific keys such as in-process scope keys, mem0 user/agent/run ids, or Graphiti group ids.
- Workspace confines file paths under tenant/agent roots and rejects traversal.
- Workflow ledger stores list/get/save by `WorkScope` and tenant-indexed columns in SQL.
- Team directory repositories require tenant arguments and filter by tenant.
- Agent collaboration uses tenant-qualified `AgentRef` and denies cross-tenant talk by default.
- Tenant routers select a physical backend/runtime per tenant where hard silos are needed.

## Rules for New Code

1. Accept explicit scope arguments at public boundaries.
2. Do not use process-global tenant state.
3. Do not convert tenant IDs with ad hoc string parsing when a scope DTO exists.
4. Keep cross-tenant collaboration denied by default unless a host policy explicitly allows it.
5. Add tests where a value written under one tenant cannot be read from another.
6. For routers, forward the full backend protocol so tenant isolation does not drop options or methods.

## Router Inventory

- `TenantReasoningStoreRouter`
- `TenantMemoryBackendRouter`
- `TenantWorkspaceBackendRouter`
- `TenantWorkStoreRouter`
- `TenantProcedureStoreRouter`
- `TenantWorkflowEngineRouter`
- `TenantOrgStoreRouter`

Routers are a production silo tool, so protocol conformance tests should cover every method they forward.

## App-Facing Rule

Application code should start with `from coactra import Scope` and convert outward only at package boundaries. Use `to_workflow_kwargs()` for procedure/runtime state, `to_work_kwargs()` for `WorkScope`, `to_memory_kwargs()` for memory, and `to_workspace_kwargs()` for workspace desks. Do not pass package-specific `Scope` objects across package boundaries.
