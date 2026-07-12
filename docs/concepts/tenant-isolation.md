# Tenant Isolation

Tenant isolation is a design constraint across the library. Every package should receive an explicit scope or tenant-qualified reference rather than inferring tenancy from global state.

## Scope Shapes

| Package | Scope shape | Purpose |
|---|---|---|
| `coactra` | `Scope(tenant_id, namespace, agent_id, session_id)` | Canonical scope shared by every package. |
| `coactra[agent]` | canonical `Scope` | Agent runtime and collaboration policy scope. |
| `coactra[memory]` | canonical `Scope` | Memory partitioning across tenant/shared/agent/session levels. |
| `coactra[workspace]` | canonical `Scope` | Path-safe filesystem/sandbox root at the workspace boundary. |
| `coactra[workflow]` | canonical `Scope` | Procedure, workflow, and durable ledger partition. |
| `coactra[team]` | tenant on root/org/store operations | Tenant is the team directory isolation boundary. |

## Isolation Mechanisms

- Memory encodes tenant into backend-specific keys such as in-process scope keys, mem0 user/agent/run ids, or Graphiti group ids.
- Workspace confines file paths under tenant/agent roots and rejects traversal.
- Workflow ledger stores list/get/save by canonical `Scope` and tenant-indexed columns in SQL.
- Team directory repositories require tenant arguments and filter by tenant.
- Agent collaboration uses tenant-qualified `AgentRef` and denies cross-tenant talk by default.
- Tenant routers select a physical backend/runtime per tenant where hard silos are needed.

## Rules for New Code

1. Accept explicit scope arguments at public boundaries.
2. Do not use process-global tenant state.
3. Do not convert tenant IDs with ad hoc string parsing when a scope DTO exists.
4. Keep cross-tenant collaboration denied by default unless a host policy explicitly allows it.
5. Add tests where a value written under one tenant cannot be read from another.
6. For routers, forward only the memory/tool/workspace contracts the wrapped object supports.

## Router Inventory

- `TenantReasoningStoreRouter`
- `TenantMemoryRouter`
- `TenantWorkspaceBackendRouter`
- `TenantWorkStoreRouter`
- `TenantProcedureStoreRouter`
- `TenantWorkflowEngineRouter`
- `TenantOrgStoreRouter`

Routers are a production silo tool, so protocol conformance tests should cover every method they forward.

## App-Facing Rule

Application code should start with `from coactra import Scope` and pass that same value across package boundaries. Shared pools use `agent_id=None`; private memory/workspaces set `agent_id`; sessions set `session_id`.
