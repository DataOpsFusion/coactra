# Chatbot Knowledge Base

Purpose: compact, searchable project knowledge chunks for an AI agent or RAG index. Each chunk separates facts from likely questions and cites the source files that support it.

## KB Chunk: Project Overview

Summary:
Coactra is a multi-package Python toolkit for AI agents that need durable work, reusable workflows, long-term memory, persistent workspaces, organization/authorization context, and a composition/policy agent layer. It is alpha-quality library infrastructure, not a single deployed application.

Keywords:
coactra, agent systems, multi-package, alpha, durable work, memory, workspace, organization, orchestration

Related files:

- `README.md`
- `docs/LIBRARIES.md`
- `docs/INTERFACES.md`
- `docs/PRODUCTION.md`

Related components:

- `coactra-agent`
- `coactra-jobs`
- `coactra-memory`
- `coactra-workspace`
- `coactra-directory`
- `coactra-ai`

Questions this chunk can answer:

- What is this project?
- Is this a web app or a library?
- What problem does Coactra solve?
- How mature is the codebase?

## KB Chunk: Package Boundary Map

Summary:
The monorepo contains six main capability packages plus an umbrella package. `coactra-ai` handles model utilities and reasoning replay. `coactra-memory` handles remember/recall. `coactra-workspace` provides an agent desk. `coactra-jobs` combines durable work orders and workflows. `coactra-directory` models tenants, hierarchy, permissions, and authorization. `coactra-agent` wires these through ports and owns session-level policy.

Keywords:
package boundaries, coactra-ai, coactra-memory, coactra-workspace, coactra-jobs, coactra-directory, coactra-agent

Related files:

- `docs/LIBRARIES.md`
- `coactra/pyproject.toml`
- `lib-ai/pyproject.toml`
- `memory/pyproject.toml`
- `workspace/pyproject.toml`
- `jobs/pyproject.toml`
- `directory/pyproject.toml`
- `agent/pyproject.toml`

Related components:

- package metadata
- optional extras
- public API roots

Questions this chunk can answer:

- Which packages exist?
- Which package owns memory?
- Which package owns workflow execution?
- Where should new agent composition code live?

## KB Chunk: Canonical Scope and Tenant Isolation

Summary:
Tenant isolation is a cross-cutting concept. `CoactraScope` is the canonical DTO that converts tenant, namespace, agent, and session identifiers into package-specific scope kwargs. Each package also has its own scope type for its local constraints, such as path-safe workspace scopes and memory scopes with namespace/agent/session keys.

Keywords:
scope, tenant isolation, CoactraScope, namespace, agent_id, session_id, scope key

Related files:

- `coactra/src/coactra/scope.py`
- `coactra/tests/test_scope.py`
- `memory/src/coactra/memory/types.py`
- `workspace/src/coactra/workspace/scope.py`
- `agent/src/coactra/agent/domain/scope.py`
- `jobs/src/coactra/jobs/work/domain/scope.py`
- `docs/INTERFACES.md`

Related components:

- `CoactraScope`
- memory `Scope`
- workspace `Scope`
- jobs/workflow/agent scope objects
- tenant routers

Questions this chunk can answer:

- How does tenant isolation work?
- How do I convert one scope shape to another?
- Why are there multiple Scope classes?
- What should be included in memory scope metadata?

## KB Chunk: Agent Composition Root and Ports

Summary:
`coactra-agent` is a composition and policy layer, not a monolithic agent framework. It consumes six capability ports: AI, memory, workspace, workflow, organization, and work. `make_agent` wires defaults or injected ports. `make_coactra_agent` adapts real sibling facades while preserving package boundaries.

Keywords:
agent, make_agent, make_coactra_agent, ports, DI, composition root, facade

Related files:

- `agent/src/coactra/agent/agent.py`
- `agent/src/coactra/agent/factory.py`
- `agent/src/coactra/agent/ports/protocols.py`
- `agent/src/coactra/agent/ports/fakes.py`
- `agent/src/coactra/agent/integrations/adapters.py`
- `agent/src/coactra/agent/integrations/factory.py`
- `agent/tests/test_agent.py`
- `agent/tests/test_integrations_factory.py`

Related components:

- `Agent`
- `AIPort`
- `MemoryPort`
- `WorkspacePort`
- `WorkflowPort`
- `OrganizationPort`
- `WorkPort`

Questions this chunk can answer:

- How is an agent constructed?
- Where are dependencies injected?
- How does agent call memory/workspace/workflow?
- How do real sibling packages connect to agent?

## KB Chunk: MCP Mounting and Tool Visibility

Summary:
The agent owns session-level MCP mounting. A server exposes bare tool names through `MCPServerPort`. `MountRegistry` stages mounts as pending and only promotes them to active at `begin_turn`. `ToolTrie` stores qualified names such as `fs.read_file`, supports prefix lookup, and delegates terminal conflicts to a `ConflictPolicy`.

Keywords:
MCP, tools, mount, next safe turn, begin_turn, ToolTrie, MountRegistry, conflict policy

Related files:

- `agent/src/coactra/agent/mounting.py`
- `agent/src/coactra/agent/agent.py`
- `agent/tests/test_mounting.py`
- `agent/tests/test_agent.py`
- `workspace/src/coactra/workspace/integrations/mcp.py`

Related components:

- `MCPServerPort`
- `ToolSpec`
- `ToolTrie`
- `MountRegistry`
- `NamespaceByMountId`
- `RejectOnConflict`

Questions this chunk can answer:

- When do newly mounted MCP tools become visible?
- How are tool name conflicts resolved?
- Why are tool names qualified by mount id?
- Where should MCP servers be mounted?

## KB Chunk: Delegated Identity and Token Exchange

Summary:
Delegated identity follows the RFC 8693 token-exchange model. Raw subject tokens must not be passed downstream. `InProcessExchanger` provides a no-network default that mints an opaque token and stores an immutable actor chain. `KeycloakExchanger` and `AsyncKeycloakExchanger` implement real token exchange against a Keycloak-compatible endpoint.

Keywords:
delegated identity, RFC 8693, token exchange, Keycloak, no passthrough, actor chain, Hop

Related files:

- `agent/src/coactra/agent/domain/identity.py`
- `agent/src/coactra/agent/identity.py`
- `agent/src/coactra/agent/adapters/keycloak.py`
- `agent/src/coactra/agent/conformance.py`
- `agent/tests/test_identity.py`
- `agent/tests/test_keycloak_adapter.py`
- `agent/tests/test_async_identity.py`

Related components:

- `DelegationGrant`
- `Hop`
- `ExchangedIdentity`
- `TokenExchanger`
- `InProcessExchanger`
- `CachedAsyncTokenExchanger`
- `KeycloakExchanger`

Questions this chunk can answer:

- How does an agent act on behalf of a human?
- How is token passthrough prevented?
- How are multi-hop delegation chains represented?
- How does Keycloak integration work?

## KB Chunk: Collaboration Policy and A2A

Summary:
Coactra does not fork A2A. It keeps collaboration policy above the A2A transport. `AllowSameTenant` denies cross-tenant targets and optionally limits which agents may talk. `PolicyGatedCollaborator` gates requests before any wire call. Official A2A outbound and inbound adapters handle SDK-specific details.

Keywords:
A2A, collaboration, policy gate, cross tenant denial, OfficialA2ATransport, Starlette, inbound A2A

Related files:

- `agent/src/coactra/agent/collaboration.py`
- `agent/src/coactra/agent/adapters/a2a.py`
- `agent/src/coactra/agent/adapters/a2a_server.py`
- `agent/tests/test_collaboration.py`
- `agent/tests/test_a2a_adapter.py`
- `agent/tests/test_a2a_server.py`
- `examples/projects/multi_agent_policy/app.py`

Related components:

- `AgentRef`
- `AllowSameTenant`
- `PolicyGatedCollaborator`
- `AsyncPolicyGatedCollaborator`
- `OfficialA2ATransport`
- `A2AInboundRequest`
- `build_a2a_app`

Questions this chunk can answer:

- How does agent-to-agent collaboration work?
- Where does A2A fit?
- How are cross-tenant A2A calls blocked?
- How do I expose an inbound A2A endpoint?

## KB Chunk: AI Completion and Structured Output

Summary:
`coactra-ai` wraps LiteLLM and Instructor. `BoundCompleter` calls `litellm.completion`; `ask` extracts text from content or reasoning-like fields; `structured` uses Instructor and defaults to JSON mode to avoid provider tool-mode incompatibilities. `Client` binds model, API base, key, and defaults.

Keywords:
LiteLLM, Instructor, ask, structured, JSON mode, response extraction, model client

Related files:

- `lib-ai/src/coactra/ai/completion/client.py`
- `lib-ai/src/coactra/ai/client.py`
- `lib-ai/src/coactra/ai/__init__.py`
- `lib-ai/tests/test_client.py`
- `memory/src/coactra/memory/integrations/graphiti_ai.py`

Related components:

- `BoundCompleter`
- `make_completer`
- `ask`
- `structured`
- `Client`
- Graphiti AI adapters

Questions this chunk can answer:

- How does Coactra call an LLM?
- How does structured output work?
- How are reasoning_content responses handled?
- Why does structured output default to JSON mode?

## KB Chunk: Embeddings, Ranking, and Reasoning Replay

Summary:
`coactra-ai` provides embedding helpers and reasoning replay. `LiteLLMEmbedding` calls LiteLLM embedding APIs. `rank_traces` uses cosine similarity. `ReasoningEngine` captures traces, updates outcomes, and chooses replay vs fresh reasoning with `AdaptiveGate`.

Keywords:
embedding, reasoning replay, ReasoningTrace, AdaptiveGate, trace ranking, token budget

Related files:

- `lib-ai/src/coactra/ai/completion/embedding.py`
- `lib-ai/src/coactra/ai/replay/engine.py`
- `lib-ai/src/coactra/ai/replay/models.py`
- `lib-ai/src/coactra/ai/replay/gate.py`
- `lib-ai/src/coactra/ai/replay/store.py`
- `lib-ai/src/coactra/ai/adapters/chroma.py`
- `lib-ai/src/coactra/ai/tokens.py`

Related components:

- `LiteLLMEmbedding`
- `ReasoningEngine`
- `ReasoningTrace`
- `RecallResult`
- `AdaptiveGate`
- `InMemoryStore`
- `ChromaStore`

Questions this chunk can answer:

- What is reasoning replay?
- How does Coactra rank prior reasoning traces?
- Where are reasoning traces stored?
- How are token counts estimated?

## KB Chunk: Memory Facade and Backends

Summary:
`coactra-memory` exposes a tiny async `Memory` facade over a `MemoryBackend` Protocol. It returns `Recollection` objects regardless of backend. The default backend is in-process and lexical. Optional mem0 and Graphiti backends are lazily imported and used only when constructed.

Keywords:
memory, remember, recall, MemoryBackend, Recollection, inprocess, mem0, Graphiti, export

Related files:

- `memory/src/coactra/memory/__init__.py`
- `memory/src/coactra/memory/types.py`
- `memory/src/coactra/memory/facade.py`
- `memory/src/coactra/memory/backends/base.py`
- `memory/src/coactra/memory/backends/inprocess.py`
- `memory/src/coactra/memory/backends/mem0.py`
- `memory/src/coactra/memory/backends/graphiti.py`
- `memory/src/coactra/memory/factory.py`
- `memory/README.md`

Related components:

- `Memory`
- `Scope`
- `Recollection`
- `MemoryBackend`
- `InProcessMemoryBackend`
- `Mem0Backend`
- `GraphitiBackend`
- `make_backend`

Questions this chunk can answer:

- How do I store and recall memory?
- What backends are supported?
- Does a mem0 or Graphiti object leak into app code?
- How does memory export work?

## KB Chunk: Memory Authorization and Tenant Routing

Summary:
Memory authorization is an optional wrapper. `AllowListMemoryAuthorizer` grants read/write access for actors and scopes. `AuthorizedMemory` checks access before remember/recall. `TenantMemoryBackendRouter` selects a different physical memory backend per tenant.

Keywords:
memory ACL, AuthorizedMemory, MemoryAccess, allowlist, tenant memory router, scope authorization

Related files:

- `memory/src/coactra/memory/authorization.py`
- `memory/src/coactra/memory/routing.py`
- `memory/tests/test_authorization.py`
- `memory/tests/test_routing.py`
- `workspace/src/coactra/workspace/integrations/organization.py`

Related components:

- `MemoryAccess`
- `MemoryAuthorizer`
- `AllowListMemoryAuthorizer`
- `AuthorizedMemory`
- `TenantMemoryBackendRouter`
- `MemoryAcl`

Questions this chunk can answer:

- How do I restrict memory reads or writes?
- How can one tenant use a different memory backend?
- How does workspace publishing to shared memory get checked?

## KB Chunk: Graphiti Integration and Provider Normalization

Summary:
The Graphiti backend wraps `graphiti_core` and maps Coactra scopes into Graphiti group IDs. It includes normalization for OpenAI-compatible providers that return `entities` where Graphiti expects `extracted_entities`. It can also build Graphiti LLM/embed/reranker clients from `coactra-ai` objects.

Keywords:
Graphiti, Neo4j, group_id, extracted_entities, OpenAI-compatible, Qwen, GraphitiAIClient

Related files:

- `memory/src/coactra/memory/backends/graphiti.py`
- `memory/src/coactra/memory/integrations/graphiti_ai.py`
- `memory/tests/test_graphiti_backend.py`
- `memory/tests/test_graphiti_group_id.py`
- `memory/tests/test_graphiti_ai_integration.py`
- `memory/README.md`

Related components:

- `GraphitiBackend`
- `_group_id`
- `_normalize_extracted_entities_response`
- `_patch_generate_response`
- `GraphitiAIClient`
- `GraphitiEmbeddingClient`
- `GraphitiEmbeddingReranker`

Questions this chunk can answer:

- How does Coactra integrate with Graphiti?
- Why is Graphiti provider output normalized?
- How is tenant scope encoded for Graphiti?
- Can Graphiti use Coactra AI clients?

## KB Chunk: Workspace Desk and Local Execution Policy

Summary:
`coactra-workspace` provides a persistent agent desk with file operations, handoff notes, journals, and passive capability manifests. `LocalFilesystemBackend` confines paths under a tenant/agent root. Command execution is disabled by default and, when enabled, uses argv lists with deny-before-allow CLI policy.

Keywords:
workspace, desk, local filesystem, command execution, CliPolicy, handoff, journal, manifest

Related files:

- `workspace/src/coactra/workspace/desk.py`
- `workspace/src/coactra/workspace/backends/base.py`
- `workspace/src/coactra/workspace/backends/local.py`
- `workspace/src/coactra/workspace/policy.py`
- `workspace/src/coactra/workspace/models.py`
- `workspace/tests/test_local_files.py`
- `workspace/tests/test_local_exec.py`
- `workspace/tests/test_policy.py`
- `workspace/README.md`

Related components:

- `Workspace`
- `open_workspace`
- `WorkspaceBackend`
- `LocalFilesystemBackend`
- `CliPolicy`
- `ExecOptions`
- `ExecResult`
- `CapabilityManifest`

Questions this chunk can answer:

- What is an agent workspace?
- How are workspace files isolated?
- Is local command execution safe by default?
- How does an agent write a handoff note?

## KB Chunk: Workspace Integrations

Summary:
Workspace integration modules connect the desk to memory, organization ACLs, MCP tools, and candidate workflow files. These are optional and imported explicitly. Some current integrations use direct local `Path` access and should be treated as local-backend-specific until made backend-aware.

Keywords:
workspace integrations, MCP recall tool, distill journal, MemoryAcl, candidate workflow, office

Related files:

- `workspace/src/coactra/workspace/integrations/mcp.py`
- `workspace/src/coactra/workspace/integrations/memory.py`
- `workspace/src/coactra/workspace/integrations/organization.py`
- `workspace/src/coactra/workspace/integrations/workflow.py`
- `workspace/src/coactra/workspace/office.py`
- `workspace/tests/test_integrations_mcp.py`
- `workspace/tests/test_integrations_memory.py`
- `workspace/tests/test_integrations_organization.py`
- `workspace/tests/test_integrations_workflow.py`
- `workspace/tests/test_office.py`

Related components:

- `register_recall_tool`
- `distill_journal`
- `MemoryAcl`
- `propose_candidate_workflow`
- `OfficeWorkspace`

Questions this chunk can answer:

- How does workspace expose memory recall as a tool?
- How are journal facts distilled into memory?
- How can workspace propose a candidate workflow?
- Which workspace integrations are local-file-specific?

## KB Chunk: Durable Work Orders and SQL Ledger

Summary:
`coactra.jobs` models a real unit of work with lifecycle state, attempts, leases, checkpoints, approvals, elicitations, decisions, budgets, artifacts, and audit events. `WorkManager` owns lifecycle transitions. `SqlWorkStore` persists complete work order snapshots and events with optimistic concurrency.

Keywords:
WorkOrder, WorkManager, WorkStatus, lease, checkpoint, approval, artifact, SqlWorkStore, coactra_work_orders

Related files:

- `jobs/src/coactra/jobs/work/domain/models.py`
- `jobs/src/coactra/jobs/work/domain/artifacts.py`
- `jobs/src/coactra/jobs/work/domain/events.py`
- `jobs/src/coactra/jobs/work/service.py`
- `jobs/src/coactra/jobs/work/store.py`
- `jobs/src/coactra/jobs/work/backends/inmemory.py`
- `jobs/src/coactra/jobs/work/backends/sql.py`
- `docs/jobs/WORK-ORDERS.md`
- `orchestration/tests/test_work_lifecycle.py`
- `orchestration/tests/test_work_sql_store.py`

Related components:

- `WorkOrder`
- `WorkStatus`
- `Lease`
- `Attempt`
- `ApprovalRequest`
- `Artifact`
- `WorkManager`
- `InMemoryWorkStore`
- `SqlWorkStore`

Questions this chunk can answer:

- What is a work order?
- How are durable tasks persisted?
- How do workers claim and complete work?
- What database tables store work state?

## KB Chunk: Work Adapters and Runtime Boundaries

Summary:
Work adapters convert the stable work ledger vocabulary into external protocol/runtime shapes. There are adapters for official A2A agent cards/artifacts, CloudEvents, OpenTelemetry audit sinks, fsspec artifact stores, DBOS/Temporal/Dapr dispatchers, and experimental MCP task records. The work ledger remains the source of truth.

Keywords:
work adapters, A2A, CloudEvents, OpenTelemetry, fsspec, DBOS, Temporal, Dapr, MCP Tasks

Related files:

- `jobs/src/coactra/jobs/work/adapters/a2a.py`
- `jobs/src/coactra/jobs/work/adapters/cloudevents.py`
- `jobs/src/coactra/jobs/work/adapters/opentelemetry.py`
- `jobs/src/coactra/jobs/work/adapters/fsspec.py`
- `jobs/src/coactra/jobs/work/adapters/dbos.py`
- `jobs/src/coactra/jobs/work/adapters/temporal.py`
- `jobs/src/coactra/jobs/work/adapters/dapr.py`
- `jobs/src/coactra/jobs/work/adapters/mcp_tasks.py`
- `docs/jobs/WORK-ORDERS.md`

Related components:

- `to_a2a_agent_card`
- `to_cloudevent`
- `OpenTelemetryAuditSink`
- `FsspecArtifactStore`
- `DBOSDispatcher`
- `TemporalDispatcher`
- `DaprDispatcher`
- `MCPTasksAdapter`

Questions this chunk can answer:

- Does Coactra become a workflow engine?
- How do work orders map to A2A or CloudEvents?
- Which work adapters are production-ready vs experimental?

## KB Chunk: Workflow Procedures and Runtime Handlers

Summary:
`coactra.jobs.workflow` models reusable procedures made of steps. A `RunContext` carries scope, approver, collaborator, router, and escalation chain. Runtime handlers implement approvals, collaboration, and escalation seams without importing agent/organization directly.

Keywords:
Procedure, Step, workflow, RunContext, Approver, Collaborator, EscalationRouter, ask, escalate

Related files:

- `jobs/src/coactra/jobs/workflow/domain/models.py`
- `jobs/src/coactra/jobs/workflow/runtime/engine.py`
- `jobs/src/coactra/jobs/workflow/runtime/handlers.py`
- `jobs/src/coactra/jobs/workflow/runtime/approval.py`
- `orchestration/tests/test_workflow_engine_handlers.py`
- `docs/jobs/PROCEDURES.md`

Related components:

- `Procedure`
- `Step`
- `RunContext`
- `ProcedureRunner`
- `Approver`
- `Collaborator`
- `EscalationRouter`
- `InMemoryApprovalStore`

Questions this chunk can answer:

- What is a procedure?
- How do workflows ask another agent?
- How does escalation connect to organization?
- Where are approvals stored?

## KB Chunk: Durable LangGraph Engine

Summary:
`DurableLangGraphEngine` compiles workflow documents into LangGraph graphs with support for tool, python, prompt, human, ask, escalate, branch, parallel, loop, and sub-procedure nodes. It validates capabilities, gates red-tier side effects, handles interrupts/resume, verifies done criteria, scopes thread IDs by tenant, and uses checkpointers such as `MemorySaver` by default.

Keywords:
DurableLangGraphEngine, LangGraph, interrupt, resume, capability registry, red tier gate, done criteria, checkpointer

Related files:

- `jobs/src/coactra/jobs/workflow/backends/durable_langgraph.py`
- `jobs/src/coactra/jobs/workflow/runtime/capabilities.py`
- `jobs/src/coactra/jobs/workflow/runtime/verification.py`
- `jobs/src/coactra/jobs/workflow/runtime/tools.py`
- `orchestration/tests/test_workflow_durable_langgraph.py`

Related components:

- `DurableLangGraphEngine`
- `build_graph`
- `make_tool_node`
- `verify_done_criteria`
- `CapabilityRegistry`
- `WorkflowInterrupt`
- `WorkflowRun`

Questions this chunk can answer:

- How does durable LangGraph execution work?
- How are dangerous tools gated?
- What done criteria are supported?
- What is required to resume a workflow after interruption?

## KB Chunk: Workflow Induction and Promotion

Summary:
Workflow induction and promotion are experimental/library-local mechanisms for turning traces into candidate procedures and managing review/promote/rollback lifecycle. The induction module is explicitly deterministic and honest about not being full learned control flow.

Keywords:
workflow induction, AWM, candidate procedure, promotion, rollback, InMemoryProcedurePromotionStore

Related files:

- `jobs/src/coactra/jobs/workflow/induction.py`
- `jobs/src/coactra/jobs/workflow/promotion.py`
- `orchestration/tests/test_workflow_induction.py`
- `orchestration/tests/test_workflow_promotion.py`
- `workspace/src/coactra/workspace/integrations/workflow.py`

Related components:

- `induce`
- `update`
- `CandidateProcedure`
- `ProcedureVersion`
- `InMemoryProcedurePromotionStore`

Questions this chunk can answer:

- Can Coactra learn workflows?
- How are candidate procedures approved?
- How can a promoted procedure be rolled back?

## KB Chunk: Organization Domain Model

Summary:
`coactra-directory` models an AD-inspired multi-tenant OU tree. Tenants are isolation boundaries. Organization nodes contain children, members, seats, reporting/escalation metadata, policy refs, grants, and ownership. Permission resolution walks from member node up to root, respecting deny-before-allow and inheritance blocking.

Keywords:
organization, tenant, OU tree, Member, Seat, permission inheritance, reporting, escalation, ownership

Related files:

- `directory/src/coactra/directory/domain/organization.py`
- `directory/src/coactra/directory/domain/member.py`
- `directory/src/coactra/directory/domain/seat.py`
- `directory/src/coactra/directory/domain/permission.py`
- `directory/src/coactra/directory/domain/directory.py`
- `docs/directory/DESIGN.md`
- `organization/tests/test_domain_tree.py`
- `organization/tests/test_domain_permissions.py`
- `organization/tests/test_escalation.py`

Related components:

- `Organization`
- `Member`
- `Seat`
- `PermissionSet`
- `PolicyReference`
- reporting edges
- escalation routes

Questions this chunk can answer:

- What does the organization package model?
- How are permissions resolved?
- How do reporting and escalation work?
- Does organization run workflows?

## KB Chunk: Organization Persistence and Authorization

Summary:
Organization persistence is explicit: mutate an in-memory domain tree, then call `save_org`; rebuild it with `load_org`. `OrgStore` is the repository SPI. `SqliteOrgStore` is the working SQL repository, while `AsyncPostgresOrgStore` exposes async methods via worker-thread offload. Authorization is separate through `Authorizer`, with in-memory and OpenFGA implementations.

Keywords:
OrgStore, save_org, load_org, SqliteOrgStore, AsyncPostgresOrgStore, OpenFGA, AuthorizationRequest

Related files:

- `directory/src/coactra/directory/models.py`
- `directory/src/coactra/directory/repository/store.py`
- `directory/src/coactra/directory/repository/sqlite_store.py`
- `directory/src/coactra/directory/repository/async_store.py`
- `directory/src/coactra/directory/repository/routing.py`
- `directory/src/coactra/directory/service.py`
- `directory/src/coactra/directory/authorization.py`
- `directory/src/coactra/directory/adapters/openfga.py`

Related components:

- `OrgStore`
- `Directory`
- `SqliteOrgStore`
- `AsyncPostgresOrgStore`
- `TenantOrgStoreRouter`
- `AuthorizationRequest`
- `InMemoryAuthorizer`
- `OpenFGAAuthorizer`

Questions this chunk can answer:

- What database tables store org state?
- How do I save or load an organization?
- How is authorization checked?
- How can each tenant use a different org store?

## KB Chunk: Orchestration Facade

Summary:
The orchestration facade links durable work orders and workflow execution. `Orchestrator` is local/run-to-completion. `DurableOrchestrator` works with async durable engines and maps workflow run states back onto work order checkpoints, approvals, completion, and failure.

Keywords:
Orchestrator, DurableOrchestrator, work order, workflow run, checkpoint, approval, resume

Related files:

- `jobs/src/coactra/jobs/facade.py`
- `orchestration/tests/test_orchestrator.py`
- `orchestration/tests/test_durable_orchestrator.py`
- `jobs/README.md`

Related components:

- `Orchestrator`
- `DurableOrchestrator`
- `WorkManager`
- `ProcedureStore`
- `WorkflowEngine`
- `WorkflowRun`

Questions this chunk can answer:

- How are work orders linked to workflows?
- How does durable resume interact with work state?
- Which facade should a simple app use?

## KB Chunk: Adapter Maturity and Optional Extras

Summary:
Adapters have mixed maturity. Implemented/reference paths include in-process memory/work stores, local workspace backend, SQL work store, SQL org store, Keycloak exchanger, official A2A adapters, DurableLangGraphEngine, TemporalEngine, and PrefectEngine. Stub paths include workspace Daytona/E2B/OpenHands, agent FastMCP, and org Neo4j. Experimental paths include MCP Tasks and work dispatch bridges. Temporal has same-thread signal/resume semantics; Prefect uses new-run-with-prior-state unless host flow code implements stricter resume behavior.

Keywords:
adapter maturity, optional extras, stub, experimental, production seam, missing extra

Related files:

- `docs/LIBRARIES.md`
- `docs/PRODUCTION.md`
- `agent/src/coactra/agent/adapters/_stub.py`
- `agent/src/coactra/agent/adapters/fastmcp.py`
- `workspace/src/coactra/workspace/adapters/__init__.py`
- `directory/src/coactra/directory/repository/neo4j_store.py`
- `jobs/src/coactra/jobs/workflow/adapters/temporal.py`
- `jobs/src/coactra/jobs/workflow/adapters/prefect.py`

Related components:

- adapter classes
- optional extras
- missing-extra errors
- production checklist

Questions this chunk can answer:

- Which adapters are real?
- Which classes are only stubs?
- What should not be used in production?
- What extras install optional dependencies?

## KB Chunk: Examples and Function-First Style

Summary:
The examples intentionally use small functions and injected facades/ports. They demonstrate incident triage, memory recall, durable release work, workspace desks, collaboration policy, and function-first custom ports. This is the intended developer experience: use classes for durable state or external boundaries, functions for business behavior.

Keywords:
examples, function-first, incident triage, release runner, customer support memory, workspace desk, multi-agent policy

Related files:

- `docs/QUICKSTART.md`
- `docs/EXAMPLES.md`
- `examples/basic_incident_triage.py`
- `examples/function_first_agent.py`
- `examples/projects/README.md`
- `examples/projects/customer_support_memory/app.py`
- `examples/projects/release_runner/app.py`
- `examples/projects/workspace_research_desk/app.py`
- `examples/projects/multi_agent_policy/app.py`

Related components:

- `make_agent`
- `WorkManager`
- `Memory`
- `Workspace`
- `PolicyGatedCollaborator`

Questions this chunk can answer:

- How should I start building with Coactra?
- Are applications supposed to subclass Agent?
- Which example shows memory?
- Which example shows durable work?

## KB Chunk: Testing and Verification

Summary:
The repository has package-local tests for public APIs, protocols, routing, stores, lifecycle state machines, stubs, and integration adapters. Some tests are environment-gated or skip optional extras. The top-level Makefile runs package tests sequentially, with a smaller core subset.

Keywords:
tests, pytest, make test, make test-core, protocol tests, public API, optional extras

Related files:

- `Makefile`
- `agent/tests/`
- `memory/tests/`
- `workspace/tests/`
- `orchestration/tests/`
- `organization/tests/`
- `lib-ai/tests/`
- `coactra/tests/`

Related components:

- public API tests
- conformance probes
- live integration tests
- optional extra tests

Questions this chunk can answer:

- How do I run tests?
- Which invariants are covered?
- Why might tests skip?
- Where are conformance checks?

## KB Chunk: Production Guidance

Summary:
Production guidance emphasizes stable package roots, SQL work store for multi-process durable work, canonical scope conversion, sandboxed workspace execution, secret hygiene, adapter maturity checks, and capability registry verification before executing workflows.

Keywords:
production, SQL work store, sandbox, secrets, stable imports, capability registry, deployment checklist

Related files:

- `docs/PRODUCTION.md`
- `docs/INTERFACES.md`
- `docs/jobs/WORK-ORDERS.md`
- `workspace/README.md`
- `directory/README.md`
- `agent/README.md`

Related components:

- `SqlWorkStore`
- `CoactraScope`
- `LocalFilesystemBackend`
- `CapabilityRegistry`
- tenant routers

Questions this chunk can answer:

- What should I use in production?
- Which stores are process-local only?
- How should secrets be handled?
- How do I prepare workflows for production execution?

## KB Chunk: Recommended Indexing Strategy

Summary:
For chatbot retrieval, index package READMEs/DESIGNs, root docs, source modules, tests, and examples. Deprioritize generated caches, build artifacts, and lock files unless dependency pinning is needed. Add metadata for package, maturity, runtime role, statefulness, tenant behavior, dependencies, and public API status.

Keywords:
RAG, indexing, chatbot, retrieval metadata, ignore files, source chunks

Related files:

- `docs/PROJECT_DOSSIER.md`
- `docs/CHATBOT_KNOWLEDGE_BASE.md`
- `docs/IMPROVEMENT_BACKLOG.md`
- `docs/TARGET_ARCHITECTURE.md`
- `README.md`
- `docs/LIBRARIES.md`
- `docs/`

Related components:

- documentation corpus
- source index
- test index
- examples index

Questions this chunk can answer:

- What should my chatbot index?
- Which files should be ignored?
- What metadata should chunks include?
- How should code and docs be chunked?
