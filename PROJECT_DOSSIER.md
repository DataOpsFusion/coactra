# Project Dossier

Generated from a read-only inspection of the current working tree. This repository is a multi-package Python library workspace for Coactra, not a single deployed web application. Source code was not modified.

## 1. Executive Summary

Coactra is a modular toolkit for building agent systems that do real work: agents can call models, remember facts, keep a workspace, execute durable work orders, run reusable procedures, consult an organization model, and collaborate with other agents. The top-level README states that `coactra-orchestration` combines durable work orders and reusable procedures, while `coactra-agent` composes the sibling capabilities through ports (`README.md:1-7`). `LIBRARIES.md` describes six capability distributions plus a lightweight `coactra` umbrella installer (`LIBRARIES.md:7-11`, `LIBRARIES.md:116-123`).

The project is for developers building multi-tenant AI agent fleets or backend services where agents need operational boundaries: tenancy, policy, memory, durable task state, workspace persistence, delegated identity, and A2A/MCP integration. It is intentionally "thin wrappers over best-of-breed libraries" where mature tools exist, and custom code where a generalized interface gap exists (`LIBRARIES.md:27-38`).

Current maturity is alpha. The core facades and Protocols are intended stable surfaces, but multiple adapters are explicitly stubbed or experimental (`README.md:19-21`, `docs/PRODUCTION.md:92-107`, `LIBRARIES.md:187-195`). There is good unit-level coverage across packages, but production readiness depends on optional backends, durable stores, and host wiring that are only partly implemented or intentionally left as seams.

## 2. High-Level Architecture

### Main Application Type

This is a Python 3.12 multi-distribution monorepo. It publishes or intends to publish these packages:

- `coactra`: umbrella installer and shared `CoactraScope` DTO (`coactra/pyproject.toml:5-32`, `coactra/src/coactra/scope.py:26-98`).
- `coactra-ai`: model calling, structured output, embeddings, reasoning replay (`lib-ai/pyproject.toml:5-33`, `lib-ai/src/coactra/ai/__init__.py:13-45`).
- `coactra-memory`: backend-neutral long-term memory facade (`memory/pyproject.toml:5-29`, `memory/src/coactra/memory/__init__.py:1-34`).
- `coactra-workspace`: persistent agent desk and local/sandbox backend seam (`workspace/pyproject.toml:5-41`, `workspace/src/coactra/workspace/__init__.py:1-21`).
- `coactra-orchestration`: durable work orders plus reusable workflows/procedures (`orchestration/pyproject.toml:5-47`, `orchestration/src/coactra/orchestration/__init__.py:3-64`).
- `coactra-organization`: multi-tenant organization/fleet model and authorization seams (`organization/pyproject.toml:5-29`, `organization/src/coactra/organization/__init__.py:1-123`).
- `coactra-agent`: composition and policy layer over the sibling capabilities and external protocols (`agent/pyproject.toml:5-45`, `agent/src/coactra/agent/factory.py:43-107`).

There is no frontend layer, no HTTP API application other than optional inbound A2A Starlette helpers, and no Docker/Compose/CI files in the inspected `rg --files` inventory.

### Layers

```text
Application code
  |
  v
coactra.agent.Agent facade
  |-- AIPort -> coactra.ai Client / ReasoningEngine / LiteLLMEmbedding
  |-- MemoryPort -> coactra.memory Memory facade and backends
  |-- WorkspacePort -> coactra.workspace Workspace desk
  |-- WorkflowPort -> coactra.orchestration.workflow engines
  |-- WorkPort -> coactra.orchestration.work WorkManager
  |-- OrganizationPort -> coactra.organization Organization / Authorizer
  |-- MCPServerPort -> mounted tool lists exposed next safe turn
  |-- A2ATransportPort -> official A2A client/server adapters
  `-- TokenExchanger -> in-process or Keycloak RFC 8693 token exchange
```

### ASCII Architecture Diagram

```text
                                  +------------------------+
                                  | Host application       |
                                  | functions/services     |
                                  +-----------+------------+
                                              |
                                              v
                                  +------------------------+
                                  | coactra.agent          |
                                  | Agent facade + ports   |
                                  | mounting/identity/A2A  |
                                  +-----------+------------+
        +-------------------------------------+--------------------------------------+
        |                  |                  |                  |                  |
        v                  v                  v                  v                  v
+---------------+  +---------------+  +---------------+  +----------------+  +---------------+
| coactra.ai    |  | coactra.memory|  | workspace     |  | orchestration  |  | organization  |
| LiteLLM       |  | Memory facade |  | Workspace desk|  | work + workflow|  | org tree/Auth |
| Instructor    |  | mem0/Graphiti |  | local/sandbox |  | SQL/LangGraph  |  | SQL/OpenFGA   |
| replay store  |  | inprocess     |  | integrations  |  | adapters       |  | stores        |
+-------+-------+  +-------+-------+  +-------+-------+  +--------+-------+  +-------+-------+
        |                  |                  |                   |                  |
        v                  v                  v                   v                  v
 LiteLLM/OpenAI     In-process dict,     Filesystem or      SQLAlchemy tables,  SQLModel tables,
 compatible APIs,   mem0 engine,         future Daytona/    in-memory stores,   SQLite/Postgres,
 Chroma optional    Graphiti/Neo4j       E2B/OpenHands      LangGraph optional  OpenFGA optional
```

### Main Runtime Flow

The intended runtime is function-first application code that receives an injected `Agent` or small port object. `docs/QUICKSTART.md` explicitly recommends plain functions for application behavior and classes only for durable state or external boundaries (`docs/QUICKSTART.md:19-28`, `docs/QUICKSTART.md:130-145`). `make_agent(...)` builds the dependency-light default facade (`agent/src/coactra/agent/factory.py:43-107`). `make_coactra_agent(...)` adapts real sibling facades into the agent ports (`agent/src/coactra/agent/integrations/factory.py:24-69`).

### External Dependencies

- Model calls: LiteLLM and Instructor (`lib-ai/pyproject.toml:13-16`, `lib-ai/src/coactra/ai/completion/client.py:57-74`, `lib-ai/src/coactra/ai/completion/client.py:147-180`).
- Embeddings/vector search: LiteLLM embeddings and optional Chroma (`lib-ai/src/coactra/ai/completion/embedding.py:48-66`, `lib-ai/src/coactra/ai/adapters/chroma.py:37-76`).
- Memory engines: mem0 and Graphiti optional extras (`memory/README.md:102-111`, `memory/src/coactra/memory/factory.py:17-30`).
- Workflow engines: LangGraph and DurableLangGraph are implemented optional backends; `TemporalEngine` and `PrefectEngine` are now thin `WorkflowEngine` adapters over host runtime clients/deployments (`orchestration/src/coactra/orchestration/workflow/backends/langgraph.py`, `orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py`, `orchestration/src/coactra/orchestration/workflow/adapters/temporal.py`, `orchestration/src/coactra/orchestration/workflow/adapters/prefect.py`).
- Work dispatch: DBOS, Temporal, Dapr, fsspec, A2A, CloudEvents, OpenTelemetry adapters (`orchestration/docs/WORK-ORDERS.md:51-61`).
- Organization persistence/auth: SQLModel/SQLAlchemy, async Postgres wrapper, OpenFGA adapter, Neo4j stub (`organization/src/coactra/organization/repository/sqlite_store.py:1-8`, `organization/src/coactra/organization/repository/async_store.py:1-69`, `organization/src/coactra/organization/adapters/openfga.py:17-53`, `organization/src/coactra/organization/repository/neo4j_store.py:1-14`).
- Agent communication/security: official A2A SDK, Starlette, Keycloak/RFC 8693 token exchange, FastMCP stub (`agent/src/coactra/agent/adapters/a2a.py:23-40`, `agent/src/coactra/agent/adapters/a2a_server.py:77-101`, `agent/src/coactra/agent/adapters/keycloak.py:102-262`, `agent/src/coactra/agent/adapters/fastmcp.py:1-12`).

### Database, Storage, Search/RAG, MCP

Persistent state exists through Python-backed stores rather than standalone migrations:

- Work orders: `SqlWorkStore` creates `coactra_work_orders` and `coactra_work_events` tables (`orchestration/src/coactra/orchestration/work/backends/sql.py:96-138`).
- Organization directory: SQLModel table classes for tenants, departments, seats, members, memberships, reporting edges, escalation routes, policy refs, grants, and overrides (`organization/src/coactra/organization/models.py:46-163`).
- Memory: in-process dict, mem0 engine, Graphiti graph memory using tenant-scoped engine keys/group IDs (`memory/src/coactra/memory/backends/inprocess.py:33-89`, `memory/src/coactra/memory/backends/mem0.py:75-127`, `memory/src/coactra/memory/backends/graphiti.py:38-47`, `memory/src/coactra/memory/backends/graphiti.py:242-377`).
- Workspace: local filesystem root under tenant/agent path, plus day note, journal, handoff, and passive capability manifest (`workspace/src/coactra/workspace/backends/local.py:24-122`, `workspace/src/coactra/workspace/desk.py:32-204`).
- RAG/search: `coactra-memory` provides backend-neutral recall; `coactra-ai` provides embeddings and trace ranking; workspace can register recall as an MCP-style tool (`memory/src/coactra/memory/types.py:89-102`, `lib-ai/src/coactra/ai/completion/embedding.py:13-39`, `workspace/src/coactra/workspace/integrations/mcp.py:19-84`).
- MCP/tool calling: agent owns session-level mount staging and visibility; workspace can publish recall tools; orchestration has an experimental MCP Task adapter (`agent/src/coactra/agent/mounting.py:146-203`, `workspace/src/coactra/workspace/integrations/mcp.py:19-84`, `orchestration/src/coactra/orchestration/work/adapters/mcp_tasks.py:1-119`).

## 3. Repository / Folder Map

```text
library/
  README.md, LIBRARIES.md, Makefile
  docs/
  examples/
  coactra/
  lib-ai/
  memory/
  workspace/
  orchestration/
  organization/
  agent/
  dist/
```

### Root Files

- `README.md`: package overview, test commands, production seams, and alpha warning (`README.md:1-21`). Active.
- `LIBRARIES.md`: architecture philosophy, package boundaries, dependency shape, compatibility aliases, and adapter maturity matrix (`LIBRARIES.md:27-38`, `LIBRARIES.md:125-195`). Active and important for retrieval.
- `Makefile`: loops test commands across packages; `test-core` excludes `lib-ai` and `organization` from the core set (`Makefile:1-10`). Active developer tooling.
- `LICENSE`: root license.
- `dist/`: build artifacts. Generated/stale risk for AI indexing; should usually be ignored.

### `docs/`

- Purpose: cross-package interface and production guidance.
- Important files:
  - `docs/INTERFACES.md`: stable roots, `CoactraScope`, `make_agent`, A2A placement (`docs/INTERFACES.md:5-88`).
  - `docs/PRODUCTION.md`: production checklist, SQL work store, scope conversion, local exec safety, stub warnings (`docs/PRODUCTION.md:20-114`).
  - `docs/QUICKSTART.md`: function-first app style and production swap example (`docs/QUICKSTART.md:1-145`).
  - `docs/EXAMPLES.md`: example entry points and run commands (`docs/EXAMPLES.md:1-85`).
- Status: active and useful, but missing a generated API index and this dossier.

### `examples/`

- Purpose: runnable dependency-light samples.
- Important files:
  - `examples/basic_incident_triage.py`: minimal `make_agent` plus `WorkManager` incident flow (`examples/basic_incident_triage.py:39-52`).
  - `examples/function_first_agent.py`: structural ports as plain functions, custom port injection, work scope conversion (`examples/function_first_agent.py:30-130`, `examples/function_first_agent.py:138-159`).
  - `examples/projects/*`: memory, release runner, workspace desk, collaboration policy samples (`examples/projects/README.md:5-12`).
- Status: active documentation by example. Uses in-process/local defaults by design.

### `coactra/`

- Purpose: umbrella package and shared canonical scope DTO.
- Important files:
  - `coactra/pyproject.toml`: package extras for sibling libraries and deprecated aliases (`coactra/pyproject.toml:5-32`).
  - `coactra/src/coactra/scope.py`: `CoactraScope` and package-specific conversion helpers (`coactra/src/coactra/scope.py:26-98`).
  - `coactra/tests/test_scope.py`: verifies key and conversions (`coactra/tests/test_scope.py:8-58`).
- Status: active, small, useful as cross-package glue.

### `lib-ai/`

- Purpose: model/embedding utilities plus reasoning replay.
- Important files:
  - `lib-ai/src/coactra/ai/completion/client.py`: LiteLLM/Instructor completion, `ask`, `structured`, response-shape fallbacks (`lib-ai/src/coactra/ai/completion/client.py:57-214`).
  - `lib-ai/src/coactra/ai/replay/engine.py`: `ReasoningEngine` capture, outcome update, recall-or-reason (`lib-ai/src/coactra/ai/replay/engine.py:21-85`).
  - `lib-ai/src/coactra/ai/replay/store.py`: tenant-partitioned `InMemoryStore` (`lib-ai/src/coactra/ai/replay/store.py:8-23`).
  - `lib-ai/src/coactra/ai/routing.py`: tenant reasoning store router (`lib-ai/src/coactra/ai/routing.py:10-31`).
  - `lib-ai/src/coactra/ai/tokens.py`: token counters (`lib-ai/src/coactra/ai/tokens.py:8-42`).
- Status: active. Chroma optional adapter exists; live model tests are environment-dependent.

### `memory/`

- Purpose: backend-neutral long-term memory facade.
- Important files:
  - `memory/src/coactra/memory/types.py`: public `Scope`, `Recollection`, `MemoryEvent` types (`memory/src/coactra/memory/types.py:24-102`).
  - `memory/src/coactra/memory/facade.py`: async `Memory` facade and sync bridge (`memory/src/coactra/memory/facade.py:32-76`).
  - `memory/src/coactra/memory/backends/base.py`: `MemoryBackend` Protocol (`memory/src/coactra/memory/backends/base.py:34-56`).
  - `memory/src/coactra/memory/backends/inprocess.py`: offline lexical default (`memory/src/coactra/memory/backends/inprocess.py:1-12`, `memory/src/coactra/memory/backends/inprocess.py:33-89`).
  - `memory/src/coactra/memory/backends/mem0.py`: async wrapper over sync mem0 (`memory/src/coactra/memory/backends/mem0.py:1-10`, `memory/src/coactra/memory/backends/mem0.py:75-127`).
  - `memory/src/coactra/memory/backends/graphiti.py`: Graphiti backend, group ID encoding, provider output normalization (`memory/src/coactra/memory/backends/graphiti.py:38-47`, `memory/src/coactra/memory/backends/graphiti.py:65-148`, `memory/src/coactra/memory/backends/graphiti.py:242-377`).
  - `memory/src/coactra/memory/authorization.py`: read/write ACL wrapper (`memory/src/coactra/memory/authorization.py:17-83`).
  - `memory/src/coactra/memory/export.py`: lossy export report (`memory/src/coactra/memory/export.py:25-83`).
- Status: active. In-process backend works offline; mem0/Graphiti depend on optional engines and external services.

### `workspace/`

- Purpose: persistent agent desk: files, handoff, CLI policy, capability manifest, optional integrations.
- Important files:
  - `workspace/src/coactra/workspace/scope.py`: tenant/agent path-safe scope (`workspace/src/coactra/workspace/scope.py:15-32`).
  - `workspace/src/coactra/workspace/backends/base.py`: backend protocol (`workspace/src/coactra/workspace/backends/base.py:1-12`).
  - `workspace/src/coactra/workspace/backends/local.py`: confined local filesystem backend and unsafe exec opt-in (`workspace/src/coactra/workspace/backends/local.py:1-11`, `workspace/src/coactra/workspace/backends/local.py:75-122`).
  - `workspace/src/coactra/workspace/policy.py`: CLI allow/deny policy and argv conversion (`workspace/src/coactra/workspace/policy.py:1-13`, `workspace/src/coactra/workspace/policy.py:36-72`).
  - `workspace/src/coactra/workspace/desk.py`: `Workspace` facade and `open_workspace` (`workspace/src/coactra/workspace/desk.py:32-204`).
  - `workspace/src/coactra/workspace/office.py`: optional office layout/status governance/token counting (`workspace/src/coactra/workspace/office.py:18-224`).
  - `workspace/src/coactra/workspace/integrations/*`: memory, organization, MCP, workflow helpers.
- Status: active. Local backend is implemented; Daytona/E2B/OpenHands adapters are explicit stubs (`workspace/src/coactra/workspace/adapters/__init__.py:1-17`).

### `orchestration/`

- Purpose: combines durable work order lifecycle with reusable procedure/workflow execution.
- Important files:
  - `orchestration/src/coactra/orchestration/work/domain/models.py`: `WorkOrder`, lifecycle enums, attempts, approvals, budget, decisions (`orchestration/src/coactra/orchestration/work/domain/models.py:22-182`).
  - `orchestration/src/coactra/orchestration/work/service.py`: `WorkManager` lifecycle methods (`orchestration/src/coactra/orchestration/work/service.py:50-436`).
  - `orchestration/src/coactra/orchestration/work/backends/sql.py`: durable SQL work store (`orchestration/src/coactra/orchestration/work/backends/sql.py:1-295`).
  - `orchestration/src/coactra/orchestration/workflow/domain/models.py`: procedure and step models (`orchestration/src/coactra/orchestration/workflow/domain/models.py:14-110`).
  - `orchestration/src/coactra/orchestration/workflow/runtime/*`: run context, handlers, durable protocol, approval, capability validation, verification.
  - `orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py`: rich durable LangGraph backend (`orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py:1-944`).
  - `orchestration/src/coactra/orchestration/facade.py`: `Orchestrator` and `DurableOrchestrator` linking work orders to procedure runs (`orchestration/src/coactra/orchestration/facade.py:51-332`).
- Status: active but in transition from earlier `work`/`workflow` package paths. Compatibility aliases exist (`orchestration/README.md:72-78`).

### `organization/`

- Purpose: standalone multi-tenant org/fleet directory with hierarchy, permissions, reporting, escalation, persistence, and authorization seams.
- Important files:
  - `organization/src/coactra/organization/domain/organization.py`: composite org tree and permission/lifecycle methods (`organization/src/coactra/organization/domain/organization.py:29-289`).
  - `organization/src/coactra/organization/domain/member.py`: member kind/status and permission overrides (`organization/src/coactra/organization/domain/member.py:24-81`).
  - `organization/src/coactra/organization/models.py`: SQLModel table definitions (`organization/src/coactra/organization/models.py:18-163`).
  - `organization/src/coactra/organization/repository/store.py`: `OrgStore` Protocol and directory DTO (`organization/src/coactra/organization/repository/store.py:20-194`).
  - `organization/src/coactra/organization/repository/sqlite_store.py`: tenant-filtered SQL repository (`organization/src/coactra/organization/repository/sqlite_store.py:1-510`).
  - `organization/src/coactra/organization/service.py`: explicit `save_org` / `load_org` (`organization/src/coactra/organization/service.py:1-268`).
  - `organization/src/coactra/organization/authorization.py`: async authorizer seam (`organization/src/coactra/organization/authorization.py:16-90`).
  - `organization/src/coactra/organization/company.py`: bootstrap and validation helpers (`organization/src/coactra/organization/company.py:30-244`).
- Status: active. SQLite/SQLAlchemy path is implemented; Neo4j is a raise-on-use stub.

### `agent/`

- Purpose: composition/policy runtime wiring the other libraries into an agent facade.
- Important files:
  - `agent/src/coactra/agent/ports/protocols.py`: six capability ports (`agent/src/coactra/agent/ports/protocols.py:31-107`).
  - `agent/src/coactra/agent/factory.py`: `make_agent` composition root (`agent/src/coactra/agent/factory.py:43-107`).
  - `agent/src/coactra/agent/agent.py`: `Agent` facade (`agent/src/coactra/agent/agent.py:39-181`).
  - `agent/src/coactra/agent/mounting.py`: MCP mount registry, trie, next-turn promotion (`agent/src/coactra/agent/mounting.py:81-203`).
  - `agent/src/coactra/agent/identity.py`: token exchangers, no-passthrough invariant, async cache (`agent/src/coactra/agent/identity.py:44-205`).
  - `agent/src/coactra/agent/collaboration.py`: collaboration policy and sync/async A2A transport gates (`agent/src/coactra/agent/collaboration.py:52-184`).
  - `agent/src/coactra/agent/adapters/a2a.py`: official outbound A2A SDK adapter (`agent/src/coactra/agent/adapters/a2a.py:117-200`).
  - `agent/src/coactra/agent/adapters/a2a_server.py`: inbound A2A executor and Starlette app builder (`agent/src/coactra/agent/adapters/a2a_server.py:104-199`).
  - `agent/src/coactra/agent/adapters/keycloak.py`: real Keycloak-compatible token exchange (`agent/src/coactra/agent/adapters/keycloak.py:102-262`).
- Status: active. FastMCP adapter remains a stub; OpenAI Agents SDK extra is intentionally not implemented yet (`agent/pyproject.toml:41-44`).

## 4. Core Concepts and Domain Model

### Tenant and Scope

Meaning: every package models tenant isolation explicitly. The canonical DTO is `CoactraScope`, which converts to package-specific scope shapes (`coactra/src/coactra/scope.py:26-98`). Memory has `Scope(tenant, namespace, agent, session)` with reserved separator validation (`memory/src/coactra/memory/types.py:24-87`). Workspace has path-safe `Scope(tenant_id, agent_id)` (`workspace/src/coactra/workspace/scope.py:15-32`). Work/workflow/agent use `tenant_id` plus optional namespace (`orchestration/src/coactra/orchestration/work/domain/scope.py:8-18`, `agent/src/coactra/agent/domain/scope.py:14-24`).

Connections: scope keys partition memory, workspace files, work orders, workflow engines, org stores, and agent routers.

### Agent

Meaning: a facade over injected capability ports, not a monolithic agent framework. `Agent` owns session-level policy mechanisms such as tool mounting, token delegation, and collaboration (`agent/src/coactra/agent/agent.py:39-181`). `make_agent` is the composition root (`agent/src/coactra/agent/factory.py:43-107`).

Connections: delegates to AI, memory, workspace, workflow, organization, durable work, MCP servers, A2A transports, and token exchangers through ports.

### Port

Meaning: narrow structural Protocol boundaries for AI, memory, workspace, workflow, organization, and durable work (`agent/src/coactra/agent/ports/protocols.py:31-107`). Fakes make the core testable without sibling packages (`agent/src/coactra/agent/ports/fakes.py:20-158`).

Connections: `make_coactra_agent` adapts real sibling facades into ports (`agent/src/coactra/agent/integrations/adapters.py:14-168`).

### Tool and MCP Mount

Meaning: a server exposes bare tool names; `MountRegistry` stages mounts and promotes them at `begin_turn`, then exposes qualified names `<mount>.<tool>` (`agent/src/coactra/agent/mounting.py:32-203`). `ToolTrie` handles exact lookup and prefix enumeration (`agent/src/coactra/agent/mounting.py:81-143`).

Connections: `Agent.mount_mcp` and `Agent.tools` expose active tool lists to hosts/models (`agent/src/coactra/agent/agent.py:81-101`). Workspace can register memory recall as an MCP-style tool (`workspace/src/coactra/workspace/integrations/mcp.py:19-84`).

### Delegated Identity

Meaning: an agent acting for a human or upstream actor must exchange tokens rather than pass them through. `DelegationGrant`, `Hop`, and `ExchangedIdentity` model the subject/actor chain (`agent/src/coactra/agent/domain/identity.py:20-98`). `InProcessExchanger` mints opaque local tokens and refuses passthrough (`agent/src/coactra/agent/identity.py:82-115`). `KeycloakExchanger` performs RFC 8693 token exchange (`agent/src/coactra/agent/adapters/keycloak.py:102-262`).

Connections: agent calls `act_on_behalf_of` and `delegate_further`; A2A transports can receive delegation chains.

### Collaboration and A2A

Meaning: collaboration policy is separate from the A2A wire protocol. `AllowSameTenant` denies cross-tenant targets and optionally narrows intra-tenant pairs (`agent/src/coactra/agent/collaboration.py:52-79`). `PolicyGatedCollaborator` gates requests before transport (`agent/src/coactra/agent/collaboration.py:117-154`). Official A2A adapters handle outbound and inbound SDK shapes (`agent/src/coactra/agent/adapters/a2a.py:117-200`, `agent/src/coactra/agent/adapters/a2a_server.py:104-199`).

Connections: workflow `ask`/`escalate` handlers can structurally use the policy-gated collaborator.

### Memory

Meaning: backend-neutral long-term recall. `Memory` wraps an injected async `MemoryBackend` (`memory/src/coactra/memory/facade.py:55-76`, `memory/src/coactra/memory/backends/base.py:34-56`). Return shape is always `Recollection`, not engine-specific types (`memory/src/coactra/memory/types.py:89-102`).

Connections: agent `remember`/`recall`, workspace MCP recall tool, Graphiti AI integration, tenant memory router.

### Workspace

Meaning: persistent desk for an agent: files, command execution through policy, handoff, journals, manifest, optional office layout (`workspace/src/coactra/workspace/desk.py:32-204`, `workspace/src/coactra/workspace/office.py:18-224`). Local exec is disabled by default (`workspace/src/coactra/workspace/backends/local.py:75-122`).

Connections: agent workspace port, memory distillation integration, org ACL integration, candidate workflow files.

### Work Order

Meaning: one durable real-world job with lifecycle, attempts, leases, approvals, decisions, artifacts, budget, and audit events (`orchestration/src/coactra/orchestration/work/domain/models.py:22-182`). `WorkManager` implements submit/claim/start/checkpoint/approval/complete/fail/cancel/reap (`orchestration/src/coactra/orchestration/work/service.py:50-436`).

Connections: SQL work store, workflow orchestrators, A2A/MCP/CloudEvents/OTel adapters, agent work port.

### Procedure and Workflow

Meaning: reusable recipe made of steps such as task, branch, approval, ask, escalate, loops, parallel, sub-procedure depending on backend (`orchestration/src/coactra/orchestration/workflow/domain/models.py:14-110`, `orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py:366-560`). `ProcedureRunner` is the local run-to-completion protocol (`orchestration/src/coactra/orchestration/workflow/runtime/engine.py:25-45`); `WorkflowEngine` is async durable start/resume (`orchestration/src/coactra/orchestration/workflow/runtime/durable.py:50-80`).

Connections: work order facade, approval stores, capability registry, LangGraph backend, promotion store, organization escalation, agent collaborator.

### Organization

Meaning: tenant-scoped OU-like hierarchy with members, seats, permissions, ownership, reporting, escalation, and policy references (`organization/DESIGN.md:17-41`, `organization/src/coactra/organization/domain/organization.py:29-289`). Persistence is explicit through injected stores (`organization/src/coactra/organization/service.py:28-268`).

Connections: workspace memory ACL, workflow escalation chain, agent organization port, OpenFGA authorizer seam.

### Reasoning Trace

Meaning: captured reasoning and decisions can be replayed or bypassed with an adaptive quality/similarity gate (`lib-ai/src/coactra/ai/replay/models.py:10-44`, `lib-ai/src/coactra/ai/replay/engine.py:21-85`, `lib-ai/src/coactra/ai/replay/gate.py:13-32`).

Connections: intended to feed workflow induction and memory; currently local store/router implementation exists.

### Router

Meaning: tenant router classes build/cache per-tenant backends or runtimes: `TenantReasoningStoreRouter`, `TenantMemoryBackendRouter`, `TenantWorkspaceBackendRouter`, `TenantWorkStoreRouter`, `TenantProcedureStoreRouter`, `TenantWorkflowEngineRouter`, `TenantOrgStoreRouter`, `TenantAgentRouter` (`lib-ai/src/coactra/ai/routing.py:10-31`, `memory/src/coactra/memory/routing.py:12-43`, `workspace/src/coactra/workspace/routing.py:11-44`, `orchestration/src/coactra/orchestration/workflow/routing.py:13-49`, `organization/src/coactra/organization/repository/routing.py:11-50`, `agent/src/coactra/agent/routing.py:10-24`).

Connections: hard tenant silo deployments.

## 5. Main Components

### Umbrella Package: `coactra`

- Location: `coactra/`
- What it does: provides install extras and canonical cross-package `CoactraScope`.
- Important classes/functions: `CoactraScope.key`, `to_agent_kwargs`, `to_work_kwargs`, `to_memory_kwargs`, `to_workspace_kwargs`, `as_event_metadata` (`coactra/src/coactra/scope.py:26-98`).
- Inputs: tenant, namespace, agent, session ids.
- Outputs: package-specific kwargs and event metadata.
- Dependencies: dataclasses only in source; extras point to sibling packages.
- Status: active.
- Risks/problems: only one shared file; if package scope shapes change, this needs tests for every conversion.

### AI Package: `coactra.ai`

- Location: `lib-ai/src/coactra/ai/`
- What it does: model calls, structured output, embeddings, trace ranking, replay cache.
- Important classes/functions: `Client`, `make_completer`, `ask`, `structured`, `LiteLLMEmbedding`, `ReasoningEngine`, `AdaptiveGate`, `InMemoryStore`, `TenantReasoningStoreRouter`.
- Inputs: prompts, Pydantic schemas, embedding texts, reasoning traces.
- Outputs: text completions, typed objects, embeddings, ranked traces, replay decisions.
- Dependencies: LiteLLM, Instructor, Pydantic, NumPy, optional Chroma/tiktoken.
- Current status: active, with optional guarded imports so reasoning core can load without completion extras (`lib-ai/src/coactra/ai/__init__.py:13-38`).
- Risks/problems: live model behavior depends on provider response shapes; tests with optional dependencies may be skipped or environment-gated.

### Memory Package: `coactra.memory`

- Location: `memory/src/coactra/memory/`
- What it does: remember/recall/export facade over in-process, mem0, or Graphiti backends.
- Important classes/functions: `Memory`, `MemoryBackend`, `Scope`, `Recollection`, `make_backend`, `AuthorizedMemory`, `TenantMemoryBackendRouter`, `check_memory_backend_contract`.
- Inputs: event strings/dicts, query strings, scope, optional backend config.
- Outputs: `Recollection` objects, export reports.
- Dependencies: Pydantic; optional mem0, Graphiti, Graphiti AI integration.
- Current status: active. In-process backend is dependency-light; mem0/Graphiti optional.
- Risks/problems: export is intentionally lossy (`memory/src/coactra/memory/export.py:1-9`). Graphiti `dump` is a broad search approximation, not a true full graph export (`memory/src/coactra/memory/backends/graphiti.py:357-361`).

### Workspace Package: `coactra.workspace`

- Location: `workspace/src/coactra/workspace/`
- What it does: file-backed desk, command execution policy, handoff/journal/manifest, optional office profile and integrations.
- Important classes/functions: `Workspace`, `open_workspace`, `LocalFilesystemBackend`, `CliPolicy`, `OfficeWorkspace`, `TenantWorkspaceBackendRouter`.
- Inputs: workspace scope, file paths/data, command argv/string, policy, manifests.
- Outputs: files, command `ExecResult`, handoff/journal text, manifest.
- Dependencies: Pydantic; optional office/integration extras.
- Current status: local backend implemented; remote/sandbox provider adapters are stubs.
- Risks/problems: `TenantWorkspaceBackendRouter.exec` does not expose `ExecOptions` even though `WorkspaceBackend.exec` and `LocalFilesystemBackend.exec` accept options (`workspace/src/coactra/workspace/backends/base.py:48-54`, `workspace/src/coactra/workspace/backends/local.py:75-122`, `workspace/src/coactra/workspace/routing.py:43-44`). Some integrations use direct `Path` operations and are therefore local-backend-specific (`workspace/src/coactra/workspace/integrations/memory.py:21-31`, `workspace/src/coactra/workspace/integrations/workflow.py:41-47`).

### Durable Work Package: `coactra.orchestration.work`

- Location: `orchestration/src/coactra/orchestration/work/`
- What it does: durable work order vocabulary, state machine, stores, adapters.
- Important classes/functions: `WorkOrder`, `WorkStatus`, `WorkManager`, `InMemoryWorkStore`, `SqlWorkStore`, `EventEnvelope`, `Artifact`, `CapabilityDescriptor`.
- Inputs: work orders, leases, checkpoints, approvals, artifacts, decisions, budgets.
- Outputs: updated work orders, audit events, execution receipts, adapter-specific task/artifact shapes.
- Dependencies: Pydantic; optional SQLAlchemy, DBOS, Temporal, Dapr, fsspec, A2A, OTel.
- Current status: active; SQL work store implemented for production-like persistence.
- Risks/problems: optional dispatch adapters are thin bridges and marked experimental in docs; durable work ledger remains source of truth.

### Workflow Package: `coactra.orchestration.workflow`

- Location: `orchestration/src/coactra/orchestration/workflow/`
- What it does: procedure model, run context, handlers, durable engine protocols, LangGraph backends, workflow induction/promotion.
- Important classes/functions: `Procedure`, `Step`, `RunContext`, `ProcedureRunner`, `WorkflowEngine`, `DurableLangGraphEngine`, `CapabilityRegistry`, `verify_done_criteria`, `InMemoryProcedurePromotionStore`.
- Inputs: procedures/workflow docs, state dicts, approvals, tool invocations, capability specs, done criteria.
- Outputs: run results, interrupts, verification results, promoted procedure versions.
- Dependencies: Pydantic; optional LangGraph and runtime integrations.
- Current status: active; rich durable LangGraph backend exists. Temporal/Prefect workflow adapters are implemented as thin host-runtime bridges and still need real-service integration tests.
- Risks/problems: in-memory approval store is the only approval store found (`orchestration/src/coactra/orchestration/workflow/runtime/approval.py:46-81`); `TenantProcedureStoreRouter` does not implement the full `ProcedureStore` protocol (`orchestration/src/coactra/orchestration/workflow/store.py:16-40`, `orchestration/src/coactra/orchestration/workflow/routing.py:13-22`).

### Orchestration Facade

- Location: `orchestration/src/coactra/orchestration/facade.py`
- What it does: links work orders to local or durable workflow runs.
- Important classes/functions: `Orchestrator`, `DurableOrchestrator`, `_apply_run`.
- Inputs: work orders, procedures, scope, worker ids, approvals.
- Outputs: submitted/completed/paused/failed work orders and workflow run state.
- Dependencies: work manager, procedure store, workflow engine.
- Current status: active.
- Risks/problems: durable resume semantics depend on host-provided engine/checkpointer and persisted work state; document restart/resume requirements clearly.

### Organization Package: `coactra.organization`

- Location: `organization/src/coactra/organization/`
- What it does: multi-tenant org tree, membership, reporting, escalation, permissions, stores, authorizer.
- Important classes/functions: `Organization.root`, `add_child`, `hire`, `can`, `save_org`, `load_org`, `SqliteOrgStore`, `AsyncPostgresOrgStore`, `OpenFGAAuthorizer`, `TenantOrgStoreRouter`.
- Inputs: tenant ids, departments, seats, members, grants, policy refs, authorization requests.
- Outputs: org tree/domain objects, directory snapshots, authorization decisions.
- Dependencies: SQLModel/SQLAlchemy; optional Postgres/OpenFGA/Neo4j.
- Current status: active SQL path; Neo4j stub.
- Risks/problems: `AsyncPostgresOrgStore` wraps the SQL repository with worker-thread async methods (`organization/src/coactra/organization/repository/async_store.py:1-69`); naming may imply a native async driver when it is a thread-backed facade.

### Agent Package: `coactra.agent`

- Location: `agent/src/coactra/agent/`
- What it does: composition root and policy layer over sibling capabilities, MCP, A2A, and delegated identity.
- Important classes/functions: `Agent`, `make_agent`, `make_coactra_agent`, `MountRegistry`, `InProcessExchanger`, `KeycloakExchanger`, `AllowSameTenant`, `PolicyGatedCollaborator`, `OfficialA2ATransport`, `build_a2a_app`, `TenantAgentRouter`.
- Inputs: port implementations, MCP servers, delegation grants, A2A messages, scope.
- Outputs: active tool names, exchanged identities, gated collaboration results, port-delegated outputs.
- Dependencies: Pydantic; optional A2A SDK, Starlette, httpx, OAuth/Keycloak.
- Current status: active. A2A and Keycloak adapters implemented; FastMCP/OpenAI Agents integration incomplete.
- Risks/problems: package root has deprecated compatibility lookups (`agent/src/coactra/agent/__init__.py:114-145`), which helps migration but adds retrieval/API noise.

## 6. Data Flow

### User Message -> Agent -> Tools/Memory/Response

```text
user/app function
  -> Agent.think / Agent.recall / Agent.workspace_* / Agent.run_procedure
  -> injected port
  -> backend or sibling facade
  -> normalized output to app
```

Evidence:

- `Agent.think` forwards to `AIPort.ask` (`agent/src/coactra/agent/agent.py:134-181`).
- `Agent.remember` and `Agent.recall` call the async memory port with the agent scope (`agent/tests/test_agent.py:115-123`).
- `Memory` forwards to `MemoryBackend.remember/recall` and returns backend-neutral recollections (`memory/src/coactra/memory/facade.py:55-76`, `memory/src/coactra/memory/backends/base.py:34-56`).
- Default fake AI/memory/workspace/workflow ports are provided for dependency-light usage (`agent/src/coactra/agent/ports/fakes.py:20-158`).

### MCP Mount -> Next Safe Turn -> Tool Visibility

```text
Agent.mount_mcp("fs", server)
  -> MountRegistry.stage("fs", server)
  -> current turn sees old active trie
  -> Agent.begin_turn()
  -> pending mounts inserted into new ToolTrie
  -> cache invalidation callback
  -> Agent.tools() returns ["fs.read_file", ...]
```

Evidence: `MountRegistry.stage`, `begin_turn`, `active_tools`, and `lookup` implement the state machine and trie (`agent/src/coactra/agent/mounting.py:146-203`). Tests verify staged mounts are invisible until `begin_turn` (`agent/tests/test_mounting.py:87-95`, `agent/tests/test_agent.py:53-67`).

### Document/File -> Workspace -> Optional Memory Distillation

```text
Workspace.write/read/list
  -> WorkspaceBackend.write/read/list scoped to tenant/agent root
  -> optional journal/handoff/office files
  -> workspace.integrations.memory.distill_journal
  -> Memory.remember(...)
```

Evidence: `LocalFilesystemBackend` confines paths and rejects traversal (`workspace/src/coactra/workspace/backends/local.py:24-73`). `Workspace` handles files, day notes, journal rotation, and manifest (`workspace/src/coactra/workspace/desk.py:32-204`). `distill_journal` reads journal files, extracts facts, writes to memory, and marks files `.distilled` (`workspace/src/coactra/workspace/integrations/memory.py:34-77`).

### Agent Task -> Work Order -> Procedure -> Result

```text
WorkManager.submit(WorkOrder)
  -> work store save + submitted event
  -> Orchestrator/DurableOrchestrator claims and starts work
  -> procedure runner or WorkflowEngine.start/resume
  -> checkpoint/approval/complete/fail
  -> work store persists state and audit events
```

Evidence: `WorkManager.submit`, `claim`, `start`, `checkpoint`, approval methods, and terminal methods are in `work/service.py` (`orchestration/src/coactra/orchestration/work/service.py:64-294`). `Orchestrator.run` and `DurableOrchestrator.start/resume` bridge work orders and procedure/workflow runs (`orchestration/src/coactra/orchestration/facade.py:74-123`, `orchestration/src/coactra/orchestration/facade.py:160-264`, `orchestration/src/coactra/orchestration/facade.py:280-332`).

### API Request / A2A Request -> Agent Runtime -> Response

```text
A2A JSON-RPC request
  -> official SDK AgentExecutor built by make_a2a_executor
  -> parse Coactra envelope {capability, params}
  -> optional verifier checks auth/capability
  -> host handler(A2AInboundRequest)
  -> event_queue text message
```

Evidence: `parse_a2a_envelope`, `A2AInboundRequest`, `make_a2a_executor`, and `build_a2a_app` implement inbound A2A request handling (`agent/src/coactra/agent/adapters/a2a_server.py:49-199`). Tests verify verifier invocation and handler output (`agent/tests/test_a2a_server.py:57-83`).

### Tool Call -> External System -> Returned Result

```text
workflow durable LangGraph tool node
  -> render params
  -> validate capability
  -> red-tier side-effect gate may interrupt
  -> tool_invoker(name, params)
  -> state update or error
```

Evidence: `make_tool_node` requires a `tool_invoker`, validates capabilities, gates red-tier tools, and calls the invoker (`orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py:161-187`). Capability registry validation lives in `runtime/capabilities.py` (`orchestration/src/coactra/orchestration/workflow/runtime/capabilities.py:73-192`).

### Memory Write/Read Flow

```text
Memory.remember(events, scope)
  -> backend remembers under tenant/scope key
Memory.recall(query, scope, k)
  -> backend returns engine-specific hits
  -> facade/backend normalizes to Recollection
```

Evidence: `InProcessMemoryBackend` stores by `scope.key` and lexical matches (`memory/src/coactra/memory/backends/inprocess.py:33-89`). mem0 maps scope to `user_id`, `agent_id`, and `run_id` (`memory/src/coactra/memory/backends/mem0.py:29-43`, `memory/src/coactra/memory/backends/mem0.py:75-127`). Graphiti encodes `scope.key` into a legal group id and normalizes provider output drift (`memory/src/coactra/memory/backends/graphiti.py:38-47`, `memory/src/coactra/memory/backends/graphiti.py:65-148`).

### Error Handling Flow

- Work store concurrency errors and lease errors are raised to workers; docs tell workers to reload/back off on `ConflictError` or `LeaseError` (`orchestration/docs/WORK-ORDERS.md:177-180`).
- Local workspace exec fails closed unless explicitly enabled (`workspace/src/coactra/workspace/backends/local.py:75-122`).
- Token passthrough attempts raise `TokenPassthroughError` (`agent/src/coactra/agent/identity.py:90-94`, `agent/src/coactra/agent/adapters/keycloak.py:126-129`).
- Optional backend/adapters raise missing-extra errors when used without dependencies or real implementations (`workspace/src/coactra/workspace/adapters/_stub.py:10-13`, `agent/src/coactra/agent/adapters/_stub.py:10-13`, `memory/src/coactra/memory/backends/_errors.py:1-11`).
- Inbound A2A verifier or handler errors are surfaced as text error events (`agent/src/coactra/agent/adapters/a2a_server.py:126-156`).

## 7. API / Interface Inventory

### Package/Public Python Interfaces

| Interface | Input | Output | Purpose | Location |
|---|---|---|---|---|
| `coactra.scope.CoactraScope` | tenant/namespace/agent/session ids | conversion kwargs, metadata | canonical cross-package scope | `coactra/src/coactra/scope.py:26-98` |
| `coactra.ai.Client.ask` | prompt | text | model completion facade | `lib-ai/src/coactra/ai/completion/client.py:183-214` |
| `coactra.ai.Client.structured` | Pydantic schema, prompt | typed object | structured output via Instructor | `lib-ai/src/coactra/ai/completion/client.py:183-214` |
| `coactra.ai.ReasoningEngine` | query, reason function, trace data | replay or fresh decision | reasoning capture/replay | `lib-ai/src/coactra/ai/replay/engine.py:21-85` |
| `coactra.memory.Memory.remember/recall/export` | events/query/scope/backend | recollections/report | memory facade | `memory/src/coactra/memory/facade.py:55-76` |
| `coactra.memory.make_backend` | name/config | backend | memory backend factory | `memory/src/coactra/memory/factory.py:17-30` |
| `coactra.workspace.open_workspace` | scope/base/exec options | `Workspace` | open persistent or temp desk | `workspace/src/coactra/workspace/desk.py:177-204` |
| `coactra.workspace.Workspace.write/read/run` | path/data/command | file text or `ExecResult` | desk file/exec operations | `workspace/src/coactra/workspace/desk.py:32-174` |
| `coactra.orchestration.work.WorkManager` | work orders, leases, approvals | updated orders/events | durable work lifecycle | `orchestration/src/coactra/orchestration/work/service.py:50-436` |
| `coactra.orchestration.workflow.Procedure` | steps | validated procedure | reusable workflow model | `orchestration/src/coactra/orchestration/workflow/domain/models.py:14-110` |
| `coactra.orchestration.Orchestrator` | work/procedure | completed/failed/paused order | local work/procedure bridge | `orchestration/src/coactra/orchestration/facade.py:51-123` |
| `coactra.orchestration.DurableOrchestrator` | work id/scope/worker/resume | workflow run state/order | durable engine bridge | `orchestration/src/coactra/orchestration/facade.py:134-332` |
| `coactra.organization.Organization` | tenant tree/member actions | org nodes/permissions | multi-tenant org model | `organization/src/coactra/organization/domain/organization.py:29-289` |
| `coactra.organization.save_org/load_org` | org/store or tenant/store | persisted/reloaded org | explicit persistence | `organization/src/coactra/organization/service.py:28-268` |
| `coactra.agent.make_agent` | scope and ports | `Agent` | composition root | `agent/src/coactra/agent/factory.py:43-107` |
| `coactra.agent.Agent` | port calls, mounts, grants | tool names, identity, port outputs | runtime facade | `agent/src/coactra/agent/agent.py:39-181` |
| `coactra.agent.integrations.make_coactra_agent` | real sibling facades | `Agent` | full-stack adapter wiring | `agent/src/coactra/agent/integrations/factory.py:24-69` |

### CLI / Developer Commands

| Command | Purpose | Location |
|---|---|---|
| `make test` | run tests for all packages | `Makefile:1-6` |
| `make test-core` | run core package tests subset | `Makefile:7-10` |
| `PYTHONPATH=agent/src:orchestration/src python3 examples/basic_incident_triage.py` | run minimal incident example | `docs/EXAMPLES.md:5-13` |
| `PYTHONPATH=memory/src python3 examples/projects/customer_support_memory/app.py` | run memory sample | `examples/projects/README.md:5-10` |
| `PYTHONPATH=orchestration/src python3 examples/projects/release_runner/app.py` | run durable work sample | `examples/projects/README.md:5-10` |
| `PYTHONPATH=workspace/src python3 examples/projects/workspace_research_desk/app.py` | run workspace sample | `examples/projects/README.md:5-10` |
| `PYTHONPATH=agent/src python3 examples/projects/multi_agent_policy/app.py` | run collaboration sample | `examples/projects/README.md:5-10` |

### A2A Interfaces

- Outbound `OfficialA2ATransport.send(dst, question, scope) -> str`: resolves endpoint/audience, builds message, sends via official SDK (`agent/src/coactra/agent/adapters/a2a.py:167-196`).
- Inbound `make_a2a_executor(handler, verifier=...)`: builds official SDK executor (`agent/src/coactra/agent/adapters/a2a_server.py:104-171`).
- Inbound `build_a2a_app(...)`: assembles a Starlette app with agent-card and JSON-RPC routes (`agent/src/coactra/agent/adapters/a2a_server.py:174-199`).
- Security: optional verifier receives auth header and requested capability (`agent/src/coactra/agent/adapters/a2a_server.py:19-27`, `agent/src/coactra/agent/adapters/a2a_server.py:126-132`).

### MCP / Tool Interfaces

- `MCPServerPort.list_tools() -> list[str]`: server tool list protocol (`agent/src/coactra/agent/mounting.py:32-36`).
- `MountRegistry.stage/begin_turn/active_tools/lookup`: session-level MCP mount orchestration (`agent/src/coactra/agent/mounting.py:146-203`).
- `workspace.integrations.mcp.register_recall_tool`: registers memory recall tool with optional prebound aliases and publish ACL (`workspace/src/coactra/workspace/integrations/mcp.py:19-84`).
- `MCPTasksAdapter`: exposes work orders as experimental MCP Task-shaped records (`orchestration/src/coactra/orchestration/work/adapters/mcp_tasks.py:54-119`).

### Store Interfaces

- `MemoryBackend`: async remember/recall/dump/ingest/capabilities (`memory/src/coactra/memory/backends/base.py:34-56`).
- `WorkspaceBackend`: file and exec protocol (`workspace/src/coactra/workspace/backends/base.py:1-54`).
- `WorkStore` / `AtomicWorkStore`: durable work protocol (`orchestration/src/coactra/orchestration/work/store.py:17-55`).
- `ProcedureStore`: procedure persistence protocol (`orchestration/src/coactra/orchestration/workflow/store.py:16-40`).
- `ApprovalStore`: pending approval protocol (`orchestration/src/coactra/orchestration/workflow/runtime/approval.py:36-43`).
- `OrgStore`: organization repository protocol (`organization/src/coactra/organization/repository/store.py:43-194`).
- Agent ports: six capability Protocols (`agent/src/coactra/agent/ports/protocols.py:31-107`).

### Authentication/Security Interfaces

- `TokenExchanger` and `AsyncTokenExchanger`: exchange subject tokens and extend delegation chains (`agent/src/coactra/agent/identity.py:54-80`).
- `KeycloakExchanger` / `AsyncKeycloakExchanger`: RFC 8693 token exchange (`agent/src/coactra/agent/adapters/keycloak.py:102-262`).
- `Authorizer.check(AuthorizationRequest)`: async auth decision seam (`organization/src/coactra/organization/authorization.py:16-90`).
- `OpenFGAAuthorizer`: maps auth requests to OpenFGA SDK (`organization/src/coactra/organization/adapters/openfga.py:17-53`).
- `MemoryAuthorizer` and `AuthorizedMemory`: memory read/write ACLs (`memory/src/coactra/memory/authorization.py:17-83`).

## 8. Database / Storage / State

### Work SQL Store

- Tables: `coactra_work_orders` and `coactra_work_events` (`orchestration/src/coactra/orchestration/work/backends/sql.py:96-138`).
- Stored data: full `WorkOrder` JSON snapshot plus indexed `tenant_id`, `namespace`, `status`, `idempotency_key`, and `version` (`orchestration/docs/WORK-ORDERS.md:153-156`).
- Concurrency: optimistic `UPDATE ... WHERE version = ...` semantics (`orchestration/docs/WORK-ORDERS.md:177-180`, `orchestration/src/coactra/orchestration/work/backends/sql.py:145-224`).
- Use: production work ledger for multi-process workers and restart-safe work state (`docs/PRODUCTION.md:20-44`).

### Organization SQL Store

- Tables/classes: `TenantRow`, `DepartmentRow`, `SeatRow`, `MemberRow`, `MembershipRow`, `ReportingEdgeRow`, `EscalationRouteRow`, `PolicyRefRow`, `NodeGrantRow`, `MemberOverrideRow` (`organization/src/coactra/organization/models.py:46-163`).
- Stored data: tenants, org tree nodes, seats, members, memberships, reporting/escalation metadata, policy refs, node grants, member overrides.
- Use: `SqliteOrgStore` and thread-backed `AsyncPostgresOrgStore` implement tenant-filtered repository operations (`organization/src/coactra/organization/repository/sqlite_store.py:1-510`, `organization/src/coactra/organization/repository/async_store.py:1-69`).

### Memory Stores

- In-process: tenant-isolated dict, lexical recall, process-local (`memory/src/coactra/memory/backends/inprocess.py:1-12`, `memory/src/coactra/memory/backends/inprocess.py:33-89`).
- mem0: wraps sync `mem0.Memory` behind async SPI; maps scope into mem0 kwargs (`memory/src/coactra/memory/backends/mem0.py:1-10`, `memory/src/coactra/memory/backends/mem0.py:29-43`).
- Graphiti: uses Neo4j-backed temporal graph through Graphiti; encodes scope to group id and supports openai_generic normalization (`memory/src/coactra/memory/backends/graphiti.py:38-47`, `memory/src/coactra/memory/backends/graphiti.py:65-148`, `memory/src/coactra/memory/backends/graphiti.py:178-239`).
- Export: lossy cross-backend export with capability negotiation (`memory/src/coactra/memory/export.py:25-83`).

### Workspace State

- Files: local backend stores under `<base>/<tenant>/<agent>` and rejects traversal (`workspace/src/coactra/workspace/backends/local.py:24-73`).
- Journals/handoff/manifests: `Workspace` writes day notes, handoff, rotated journals, compacted output, and capability manifest (`workspace/src/coactra/workspace/desk.py:32-174`).
- Exec state: subprocess output is bounded; exec is disabled unless opt-in (`workspace/src/coactra/workspace/backends/local.py:75-122`).
- Office state: optional office layout includes templates, status schema, token counts, and office paths (`workspace/src/coactra/workspace/office.py:18-224`).

### Reasoning State

- `InMemoryStore` keeps `ReasoningTrace` objects partitioned by tenant (`lib-ai/src/coactra/ai/replay/store.py:8-23`).
- Optional Chroma adapter can persist/search traces in a vector store (`lib-ai/src/coactra/ai/adapters/chroma.py:37-76`).

### Session State

- Agent MCP mounts: pending and active tool trie live in `MountRegistry` (`agent/src/coactra/agent/mounting.py:146-203`).
- Delegated identity cache: `CachedAsyncTokenExchanger` stores TTL-scoped exchanged identities keyed by tenant, actor, audience, scopes, and token hash (`agent/src/coactra/agent/identity.py:148-205`).
- Collaboration policy: in-process allow rules live in `AllowSameTenant` (`agent/src/coactra/agent/collaboration.py:52-79`).
- Durable workflow pending thread metadata: `DurableLangGraphEngine` keeps a procedure map for thread IDs and raises if resume lacks procedure after restart (`orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py:809-944`).

### Environment Variables and Secrets

- Work docs show `COACTRA_WORK_DATABASE_URL` and `WORKER_ID` for worker setup (`orchestration/docs/WORK-ORDERS.md:160-169`).
- Memory live tests expect `OPENAI_API_KEY` and `NEO4J_URI` for live Graphiti/mem0 readiness (`memory/tests/test_live_integration.py:24-25`).
- Keycloak adapter accepts token endpoint, client id, client secret, audience, and actor tokens through constructor parameters, not environment-specific code (`agent/src/coactra/agent/adapters/keycloak.py:107-125`).
- Production docs warn not to put long-lived secrets in workspace files or capability manifests (`docs/PRODUCTION.md:82-90`).

### Logs and Generated State

- Audit events are explicit `EventEnvelope` records in work stores (`orchestration/src/coactra/orchestration/work/domain/events.py:29-39`, `orchestration/src/coactra/orchestration/work/store.py:57-70`).
- No standalone logs directory was found in the repository inventory.
- `.pytest_cache`, `.ruff_cache`, `dist`, and `uv.lock` files are generated or lock/build artifacts; index only if the chatbot needs dependency pinning.

## 9. Chatbot / Agent Readiness

### Easy for an AI Agent to Understand

- Package boundaries are documented in `LIBRARIES.md` and package READMEs (`LIBRARIES.md:95-139`).
- Public APIs are exported from package roots with tests such as `agent/tests/test_public_api.py`, `memory/tests/test_public_api.py`, `orchestration/tests/test_work_public_api.py`, and `organization/tests/test_public_api.py`.
- Protocol boundaries are explicit and small: agent ports, memory backend, workspace backend, work store, procedure store, org store.
- Tests describe many intended invariants in plain language, especially mounting, no-passthrough identity, collaboration denial, local exec safety, and Graphiti normalization.

### Hard for an AI Agent to Understand

- The repo is in a dirty transition state with many staged/unstaged renames from `work`/`workflow` to `orchestration`; both compatibility paths and new paths exist.
- Several adapters are intentionally stubs, while others are thin experimental adapters. A chatbot needs maturity metadata to avoid recommending stub classes as production-ready.
- Some production seams are documented but not fully implemented in reusable form, such as persisted approval storage.
- Optional dependency behavior is environment-dependent; tests may skip when `langgraph`, `a2a`, `sqlalchemy`, `graphiti_core`, or other extras are missing.
- Compatibility aliases and deprecated root exports create duplicate retrieval results.

### Files to Index

Index:

- `README.md`, `LIBRARIES.md`, `docs/*.md`
- package `README.md` and `DESIGN.md`
- `pyproject.toml` files
- `src/**/*.py`, excluding generated compatibility only if duplicate noise is too high
- `tests/**/*.py` for invariant documentation
- `examples/**/*.py` and `examples/**/*.md`
- the four generated docs from this request

### Files to Ignore or Deprioritize

Ignore or low-priority:

- `dist/`
- `.pytest_cache/`, `.ruff_cache/`
- `uv.lock` unless dependency lock analysis is needed
- `*.pyc`, build artifacts, generated package metadata
- deleted legacy `PLAN.md` files are not present as active docs in the current tree; do not rely on them.

### Metadata to Add

Add front matter or sidecar metadata per doc/chunk:

- package: `agent`, `memory`, `workspace`, `orchestration.work`, `orchestration.workflow`, `organization`, `ai`, `coactra`
- maturity: `implemented`, `reference`, `experimental`, `stub`, `compatibility`
- runtime role: `facade`, `protocol`, `backend`, `adapter`, `domain`, `test`, `example`, `production-doc`
- dependencies/extras
- statefulness: `stateless`, `process-local`, `file-backed`, `sql-backed`, `external-service-backed`
- tenant isolation behavior
- public API status: `stable`, `compatibility`, `internal`

### Naming and Structure Improvements for Retrieval

- Keep compatibility modules but tag them as aliases in docs.
- Add `docs/API_INDEX.md` generated from `__all__` and Protocol classes.
- Add `docs/ADAPTER_MATURITY.md` as a single source for implemented/stub/experimental adapters.
- Add `docs/STATE_AND_STORAGE.md` listing every store/table/cache.
- Add `docs/TENANT_ISOLATION.md` explaining scope semantics across packages.

## 10. Chatbot Knowledge Base Output

The companion file `CHATBOT_KNOWLEDGE_BASE.md` contains chunked, search-friendly entries. The key chunks are:

- Project Overview and Package Boundary Map
- Canonical Scope and Tenant Isolation
- Agent Composition Root and Ports
- MCP Mounting and Tool Visibility
- Delegated Identity and Keycloak Token Exchange
- Collaboration Policy and A2A Adapters
- AI Completion, Embedding, and Reasoning Replay
- Memory Facade, Backends, Authorization, and Graphiti Integration
- Workspace Desk, Local Exec Policy, and Integrations
- Durable Work Orders and SQL Ledger
- Workflow Procedures, Durable LangGraph, Capability Gates, and Approvals
- Organization Domain, Persistence, and Authorization
- Adapter Maturity and Optional Extras
- Examples and Function-First App Style
- Testing, Production Guidance, and Retrieval Indexing

Each KB chunk includes summary, keywords, related files, related components, and questions it can answer.

## 11. Improvement Backlog

The companion file `IMPROVEMENT_BACKLOG.md` contains the prioritized backlog. Highest-signal items:

- Fix workspace router `exec` signature to forward `ExecOptions`.
- Complete `TenantProcedureStoreRouter` so it satisfies the full `ProcedureStore` contract.
- Add or document a durable approval store for production workflow approvals.
- Replace direct `Path` file access in workspace integrations with backend/facade operations or mark them local-only.
- Add CI/test matrix for optional extras and integration seams.
- Add API, state/storage, adapter maturity, and tenant isolation docs for chatbot retrieval.
- Clarify restart/resume contracts for durable LangGraph workflows.

## 12. Stale / Dead / Confusing Areas

### Stub or Experimental Areas

- FastMCP adapter is a stub (`agent/src/coactra/agent/adapters/fastmcp.py:1-12`).
- Workspace Daytona/E2B/OpenHands adapters are stubs (`workspace/src/coactra/workspace/adapters/daytona.py:1-13`, `workspace/src/coactra/workspace/adapters/e2b.py:1-13`, `workspace/src/coactra/workspace/adapters/openhands.py:1-13`).
- Organization Neo4j store is a stub (`organization/src/coactra/organization/repository/neo4j_store.py:1-14`).
- Workflow Temporal and Prefect adapters are implemented thin bridges (`orchestration/src/coactra/orchestration/workflow/adapters/temporal.py`, `orchestration/src/coactra/orchestration/workflow/adapters/prefect.py`); production readiness depends on host runtime wiring and integration tests.
- MCP Tasks adapter is experimental by docs (`orchestration/docs/WORK-ORDERS.md:90-97`).
- DBOS/Temporal/Dapr dispatch adapters are documented as thin/experimental integration bridges (`LIBRARIES.md:195`).

### Duplicate or Compatibility Paths

- `coactra.work` and `coactra.workflow` compatibility aliases remain after packaging-level merge (`orchestration/README.md:72-78`, `LIBRARIES.md:179-185`).
- Agent root deprecated exports still resolve internal adapter names (`agent/src/coactra/agent/__init__.py:114-145`).
- Organization compatibility imports for older store paths remain (`organization/README.md:47-51`).
- Workspace compatibility imports for `backend.py` and `local.py` remain (`workspace/README.md:76-77`).

### Confusing or Incomplete Areas

- `AsyncPostgresOrgStore` is async by thread offload over SQLAlchemy-style repository methods, not clearly a native async DB driver (`organization/src/coactra/organization/repository/async_store.py:1-69`).
- `TenantWorkspaceBackendRouter.exec` loses command options (`workspace/src/coactra/workspace/routing.py:43-44`).
- `TenantProcedureStoreRouter` only exposes part of `ProcedureStore` (`orchestration/src/coactra/orchestration/workflow/routing.py:13-22`).
- Durable workflow approval storage is in-memory only in reusable code (`orchestration/src/coactra/orchestration/workflow/runtime/approval.py:46-81`).
- Graphiti export/dump is an approximate empty-query search, not a complete engine-native export (`memory/src/coactra/memory/backends/graphiti.py:357-361`).
- No standalone migration files exist for SQL stores; schemas are source-defined.

### Missing Tests or Coverage Gaps

- Router protocol completeness for workspace and workflow routers.
- Durable approval persistence across process restart.
- Workspace integrations against non-local backends.
- Production A2A inbound app with durable task store and real verifier.
- Cross-package integration tests for `make_coactra_agent` with real sibling facades rather than mostly fakes.

## 13. Suggested Target Architecture

The companion file `TARGET_ARCHITECTURE.md` contains the detailed recommendation. Summary:

- Keep the six capability packages plus the umbrella installer.
- Add a small shared core/docs layer for scope, maturity metadata, and generated API/state indexes.
- Keep `agent` as the only composition/policy layer; do not move memory/workspace/workflow/org logic into it.
- Keep `orchestration.work` and `orchestration.workflow` independent inside one distribution, with explicit compatibility aliases.
- Move local-only workspace integrations behind backend-aware APIs or label them clearly.
- Promote production backends to explicit reference implementations: SQL work store, SQL org store, Keycloak exchanger, Official A2A adapters.
- Keep stub adapters, but move all maturity status into one machine-readable adapter registry for chatbot retrieval.

Suggested high-level folder shape:

```text
docs/
  API_INDEX.md
  ADAPTER_MATURITY.md
  STATE_AND_STORAGE.md
  TENANT_ISOLATION.md
  ARCHITECTURE.md
packages/
  coactra/
  coactra-ai/
  coactra-memory/
  coactra-workspace/
  coactra-orchestration/
  coactra-organization/
  coactra-agent/
examples/
tests-integration/
```

## 14. Questions for the Owner

### Product Goal

- Is Coactra primarily a publishable public library suite, a private homelab agent runtime substrate, or both?
- Which package should be the first production-quality reference implementation?
- Should "agent" remain a Python library only, or eventually ship an HTTP service/runtime?

### User Experience

- Should app developers start with `make_agent`, `make_coactra_agent`, or package-specific facades?
- Should examples remain function-first, or should there be service templates?
- Which examples should become end-to-end reference apps?

### Agent Behavior

- What is the exact model-turn boundary for mounted MCP tools in hosted runtimes?
- Should collaboration policy default to same-tenant open or explicit allowlist?
- How should agent retry/escalation policy combine org hierarchy and workflow state?

### Memory/Search Design

- Is `coactra-ai` reasoning replay meant to write to `coactra-memory`, maintain a separate reasoning store, or both?
- What metadata should every memory event carry?
- Which docs and source files should be indexed into your chatbot first?

### Deployment

- Which production backend combination is the reference: Postgres + Graphiti/Neo4j + Keycloak + A2A?
- Do you want Docker/Compose templates for local integration tests?
- Should SQL stores get migration tooling such as Alembic?

### Security

- What is the tenant isolation threat model: accidental leakage, hostile tenant, or regulated hard silo?
- Should local workspace exec ever be allowed outside developer machines?
- Where should secrets live relative to workspace manifests and memory?

### Scaling

- Should tenant routers cache forever or support eviction/lifecycle hooks?
- How many tenants/agents/work orders are expected?
- Which stores need async-native implementations rather than worker-thread wrappers?

### Maintenance

- How long should compatibility aliases remain?
- Should adapter stubs stay in public imports or move to docs until implemented?
- What release/versioning policy should align package versions?

## 15. Final Summary

You have built a modular Python agent-systems library suite. Its strongest parts are the clear package boundaries, explicit Protocol seams, tenant-aware scope modeling, durable work-order vocabulary, local workspace safety defaults, memory backend neutrality, and agent-side policy mechanisms for MCP mounting, delegated identity, and A2A collaboration.

The weakest parts are production completeness and retrieval clarity: several adapters are stubs or experimental, compatibility aliases create duplicate API surfaces, some routers do not fully match their protocols, durable workflow approval persistence is not yet complete as a reusable backend, and production deployment artifacts/migrations are absent.

Improve first: fix small protocol mismatches, add adapter maturity/state/API docs, clarify durable workflow restart requirements, and add CI/integration coverage for optional extras. The next documentation to generate should be `API_INDEX.md`, `ADAPTER_MATURITY.md`, `STATE_AND_STORAGE.md`, and `TENANT_ISOLATION.md`.
