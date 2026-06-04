# Target Architecture

This target architecture preserves the current project direction: a modular Python library suite for real-work agent systems. It does not propose turning Coactra into a monolithic service or replacing mature protocols like A2A, MCP, LiteLLM, Instructor, LangGraph, Graphiti, SQLAlchemy, Keycloak, or OpenFGA.

## 1. Architecture Goals

1. Keep packages independently usable.
2. Keep `coactra-agent` as the composition and policy layer.
3. Keep durable state behind explicit stores.
4. Keep tenant isolation visible in every boundary.
5. Keep production adapter maturity clear.
6. Make the codebase easy for chatbots to index and reason about.
7. Avoid source-level coupling between sibling packages except through explicit `integrations/` modules.

## 1.1 Research-Informed Architecture Decision

The external framework research strengthens the current direction: Coactra should stay a thin domain and policy shell over mature runtimes, not compete with those runtimes.

Decision:

- Keep Coactra's unique surface: scope, tenant isolation, organization policy, workspace desk semantics, work-order ledger, approval/audit vocabulary, adapter maturity metadata, and cross-capability composition.
- Delegate commodity runtime behavior: model/provider normalization, structured output retries, graph checkpointing, workflow replay/recovery, scheduling, and plugin dispatch should come from focused libraries wherever possible.
- Do not introduce a new monolithic framework layer. If a `Kernel` concept is added later, it should be a small composition root over existing packages, not a replacement for `coactra-agent`.

Recommended adopt-first stack:

| Concern | Preferred direction | Why |
|---|---|---|
| Stateful agent procedure runtime | LangGraph as default | It matches the current `WorkflowEngine` shape: checkpointed threads, human interrupts, state inspection, and resume. |
| Hard durable execution | Temporal adapter | Best fit for crash/retry/replay guarantees that should not be reimplemented in Coactra. |
| Pythonic workflow deployment | Prefect adapter | Useful for deployment-triggered Python flows, but weaker than Temporal for same-thread signal/resume semantics. |
| Typed agent/application API | Evaluate PydanticAI patterns | Good reference for typed dependencies, tools, structured output, and durable execution integrations without forcing a rewrite. |
| Provider normalization | Keep LiteLLM/Instructor behind `coactra-ai` | Coactra should normalize provider and structured-output behavior at the adapter boundary, not reimplement model client diversity. |
| Plugin system | Add only when needed; consider pluggy | Official hooks should be small and stable. Avoid ad hoc callbacks becoming hidden public APIs. |

This means the next architecture work should narrow, not widen, the public API. First freeze the stable shell and port contracts; then add or mature adapters behind those ports.

## 2. What Should Stay

### Keep the six-package capability model

The current package split is coherent and should stay:

- `coactra-ai`: model calls, structured output, embeddings, reasoning replay.
- `coactra-memory`: backend-neutral long-term memory.
- `coactra-workspace`: persistent agent desk and execution policy.
- `coactra-orchestration`: durable work orders plus reusable workflow procedures.
- `coactra-organization`: tenant/org/permission/authorization directory.
- `coactra-agent`: composition, MCP mounting, delegated identity, collaboration policy.

Evidence: `docs/LIBRARIES.md` defines these packages and their dependency shape (`docs/LIBRARIES.md:116-139`). The agent design locks ports and dependency injection (`docs/agent/DESIGN.md:11-23`).

### Keep function-first application style

Application behavior should remain plain functions over injected facades/ports. Classes should own durable state, backend boundaries, or long-lived facades.

Evidence: `docs/QUICKSTART.md:19-28`, `docs/QUICKSTART.md:130-145`, `examples/function_first_agent.py:1-8`.

### Keep Protocols as the integration surface

The project already uses small Protocols for ports and backends. This makes packages testable with fakes and keeps adapters swappable.

Evidence:

- Agent ports: `agent/src/coactra/agent/ports/protocols.py:31-107`
- Memory backend: `memory/src/coactra/memory/backends/base.py:34-56`
- Workspace backend: `workspace/src/coactra/workspace/backends/base.py:1-54`
- Work store: `orchestration/src/coactra/orchestration/work/store.py:17-55`
- Procedure store: `orchestration/src/coactra/orchestration/workflow/store.py:16-40`
- Org store: `organization/src/coactra/organization/repository/store.py:43-194`

Target rule: every public Protocol should have a reusable conformance test suite. The goal is not just type compatibility; every adapter and tenant router should prove the same behavioral contract.

### Keep thin wrappers around mature protocols

Coactra should continue wrapping mature external protocols and engines rather than forking them:

- LiteLLM + Instructor for model calls and structured output.
- Graphiti/mem0 for memory engines.
- LangGraph/Temporal/Prefect as workflow backends.
- A2A for agent-to-agent wire protocol.
- MCP for tools and live tool changes.
- Keycloak/RFC 8693 for delegated identity.
- OpenFGA for authorization.

Evidence: `docs/LIBRARIES.md:27-38`, `agent/README.md:5-18`, `memory/README.md:8-16`, `docs/orchestration/WORK-ORDERS.md:90-97`.

### Keep the public shell smaller than the package graph

The research suggests a `Kernel` / `Session` / `Scope` / `Task` shell. That is directionally right, but the current repo already has a partial shell:

- `CoactraScope` is the canonical cross-package scope DTO.
- `coactra.agent.make_agent` and `coactra.agent.integrations.make_coactra_agent` are today's composition roots.
- `WorkManager`, `WorkOrder`, `Procedure`, `DurableOrchestrator`, and `WorkflowEngine` are today's durable work and workflow shell.

Near-term target:

1. Document these as the current stable shell.
2. Mark deeper imports, compatibility aliases, and adapter-specific classes by maturity.
3. Add a `Kernel` only if repeated app wiring proves that `make_coactra_agent` is not enough.

Do not add a broad `Kernel` class just because other frameworks have one. Add it only if it removes real application wiring complexity while preserving package independence.

## 3. What Should Be Split

### Split documentation into source-of-truth documents

Current docs are good but broad. Add focused docs:

```text
docs/
  ARCHITECTURE.md
  API_INDEX.md
  ADAPTER_MATURITY.md
  STATE_AND_STORAGE.md
  TENANT_ISOLATION.md
  SECURITY.md
  BOUNDARIES.md
  INDEXING.md
```

Why:

- `docs/PROJECT_DOSSIER.md` is a snapshot. Long-term docs should be maintained as source of truth.
- Adapter maturity and persistent state should be queryable without scanning source.
- Chatbot retrieval needs smaller, labeled chunks.

### Split optional integration tests from package unit tests

Suggested structure:

```text
tests-integration/
  memory_graphiti/
  memory_mem0/
  orchestration_langgraph/
  orchestration_sql/
  agent_a2a/
  agent_keycloak/
  organization_openfga/
  organization_postgres/
```

Why:

- Optional extras depend on external services or heavy libraries.
- Unit tests should remain fast and dependency-light.
- Integration tests can run in CI matrix jobs or manually with local infrastructure.

### Split generated distribution artifacts out of chatbot indexes

Keep `dist/`, caches, and lock files in the repo if needed, but exclude them from semantic search by default.

Suggested ignore patterns:

```text
dist/**
.pytest_cache/**
.ruff_cache/**
**/__pycache__/**
*.pyc
**/*.egg-info/**
**/uv.lock
```

Use lock files only for dependency auditing.

## 4. What Should Be Renamed or Clarified

### Clarify `AsyncPostgresOrgStore`

Current state: `AsyncPostgresOrgStore` wraps SQL repository calls with worker-thread async forwarding (`organization/src/coactra/organization/repository/async_store.py:1-69`).

Target choices:

1. Rename to `AsyncThreadedOrgStore` or `AsyncSqlOrgStore`, and document that it is thread-backed.
2. Or implement a native async Postgres store with async SQLAlchemy/driver semantics.

Recommended near-term path: document current behavior first, then decide whether native async is necessary.

### Clarify local-only workspace integrations

Current state: some integrations use direct `Path` operations (`workspace/src/coactra/workspace/integrations/memory.py:21-31`, `workspace/src/coactra/workspace/integrations/workflow.py:41-47`).

Target choices:

1. Move them through the workspace facade/backend.
2. Or rename/document as local-only helpers.

Recommended path: make them backend-aware where practical because remote workspace backends are part of the project vision.

### Clarify compatibility aliases

Keep compatibility paths for migration, but document preferred imports:

- Prefer `coactra.orchestration.work` over `coactra.work`.
- Prefer `coactra.orchestration.workflow` over `coactra.workflow`.
- Prefer adapter imports from `coactra.agent.adapters` rather than deprecated package-root lookups.

Evidence: `orchestration/README.md:72-78`, `agent/src/coactra/agent/__init__.py:114-145`, `organization/README.md:47-51`, `workspace/README.md:76-77`.

## 5. What Should Become a Library, Module, or Service

### Keep these as libraries

- `coactra-ai`
- `coactra-memory`
- `coactra-workspace`
- `coactra-orchestration`
- `coactra-organization`
- `coactra-agent`
- `coactra` umbrella

Reason: each package has a clear reusable API and optional backend seams.

### Add a small shared documentation/indexing module, not a runtime dependency

Do not add a heavy runtime `core` package unless duplication becomes painful. The existing `coactra` umbrella plus `CoactraScope` is enough for now.

Add docs/generation tooling instead:

```text
tools/
  generate_api_index.py
  generate_adapter_maturity.py
  generate_state_index.py
```

These can read `__all__`, Protocols, adapter manifests, and store models to generate docs. They should not be imported by runtime packages.

### Add a release and API-governance document

Add a source-of-truth release policy:

```text
docs/
  RELEASE_POLICY.md
  ROADMAP_V1.md
```

`RELEASE_POLICY.md` should define stable, beta, experimental, compatibility, and internal surfaces. `ROADMAP_V1.md` should state which surfaces must be frozen before a `1.0` release.

### Optional future service templates

If you later want deployable services, add templates rather than changing the libraries:

```text
examples/services/
  a2a_agent_service/
  durable_worker_service/
  memory_service/
```

Each service should import the libraries and wire production backends. The libraries should stay service-agnostic.

## 6. What Should Be Removed Later

Do not remove now. Mark for later cleanup after migration windows:

- Deprecated root/internal exports in `coactra.agent.__getattr__`.
- Old `coactra.work` and `coactra.workflow` compatibility aliases, after downstream users migrate.
- `organization/src/coactra/organization/__init__.py.orig`, if it is only a backup artifact.
- Stub classes from public adapter imports if they keep causing confusion. Alternative: keep them but make maturity metadata explicit.

Removal criteria:

1. Preferred import paths are documented.
2. Tests cover preferred paths.
3. Changelog announces deprecation.
4. At least one minor release passes.

## 7. Target Package Dependency Graph

```text
                         +----------------+
                         | coactra        |
                         | umbrella/scope |
                         +-------+--------+
                                 |
                                 v
  +--------------+      +----------------+      +----------------+
  | coactra-ai   |      | coactra-memory |      | workspace      |
  | model/replay |<---->| graphiti_ai    |      | desk/files     |
  +------+-------+      +-------+--------+      +-------+--------+
         |                      |                       |
         |                      |                       |
         +----------------------+-----------------------+
                                |
                                v
                         +----------------+
                         | coactra-agent  |
                         | ports/policy   |
                         +-------+--------+
                                 |
         +-----------------------+----------------------+
         |                                              |
         v                                              v
+--------------------+                         +--------------------+
| orchestration      |                         | organization       |
| work + workflow    |                         | tenant org/auth    |
+--------------------+                         +--------------------+
```

Rule: arrows into `coactra-agent` should be via ports/adapters. Sibling packages should not import each other except in explicit `integrations/` modules.

## 8. Target Runtime Flows

### Single-Agent App

```text
app function
  -> Agent
  -> AI/Memory/Workspace/Work/Workflow/Org ports
  -> injected backends
  -> app-owned result handling
```

Target requirements:

- App behavior stays function-first.
- Ports are injected at composition root.
- Scope conversion uses `CoactraScope` or explicit package scopes.
- In-process defaults are acceptable for demos only.

### Durable Worker

```text
WorkManager(SqlWorkStore)
  -> claim lease
  -> run workflow/procedure
  -> checkpoint
  -> approval/input/auth pause if needed
  -> complete/fail/cancel
  -> audit events stored durably
```

Target requirements:

- SQL work store for multi-process or restart-safe workers.
- Worker id and database URL come from service config.
- Lease conflicts cause reload/backoff.
- Approval persistence contract is explicit.

### Multi-Agent Collaboration

```text
Agent.talk(dst, question)
  -> CollaborationPolicy.can_talk(src, dst, scope)
  -> deny before wire if not allowed
  -> A2ATransport.send(...)
  -> Official A2A SDK
  -> remote A2A service verifier
  -> handler
```

Target requirements:

- Cross-tenant calls denied by default.
- Production inbound A2A always uses a verifier.
- Delegation chain and reduced audience/scopes are passed explicitly.

### Workspace and Memory

```text
Workspace writes notes/journal
  -> backend-confined storage
  -> optional backend-aware distillation
  -> Memory.remember(scope)
  -> Memory.recall(query, scope)
  -> optional MCP recall tool exposed next session
```

Target requirements:

- Local files never bypass the workspace backend unless marked local-only.
- Shared memory publish uses ACLs.
- Capability manifests store references, not secrets.

## 9. Target Storage Model

### Production-Ready Reference Stores

| State | Reference store | Notes |
|---|---|---|
| Work orders and audit events | `SqlWorkStore` | SQLAlchemy URL, SQLite for local, Postgres for production |
| Organization directory | `SqliteOrgStore` / Postgres SQL store | tenant-filtered repository, document async behavior |
| Memory | Graphiti or mem0 backend | engine-specific durability; `Recollection` remains boundary |
| Workspace | sandbox provider or local dev backend | local exec disabled by default |
| Reasoning traces | Chroma or tenant-routed store | optional; keep separate from long-term memory unless intentionally bridged |
| Token exchange cache | in-process TTL cache | convenience only, not durable authorization |
| Workflow approvals | SQL-backed store or durable work-order mapping | needs explicit target decision |

### Add Migrations or Schema Docs

Current schemas are Python-defined. For production confidence:

- Add schema docs for work SQL tables and org SQLModel tables.
- Consider Alembic migrations for work and org stores.
- Version stored JSON snapshots for work orders and workflow checkpoints.

## 10. Target Adapter Maturity Model

Create a single manifest:

```yaml
adapters:
  - package: coactra-agent
    name: OfficialA2ATransport
    file: agent/src/coactra/agent/adapters/a2a.py
    extra: a2a
    maturity: implemented
    production_notes: requires endpoint/audience/token provider from host
  - package: coactra-agent
    name: FastMCPServer
    file: agent/src/coactra/agent/adapters/fastmcp.py
    extra: mcp
    maturity: stub
    production_notes: raises on use
```

Maturity values:

- `reference`: default implementation suitable for local/dev and some production scenarios.
- `implemented`: functional adapter, production depends on host config.
- `experimental`: usable seam with unstable protocol/runtime assumptions.
- `stub`: named seam only, raises on use.
- `compatibility`: alias for migration, not preferred for new code.

Use this manifest to generate `docs/ADAPTER_MATURITY.md` and chatbot metadata.

Add one required field for runtime adapters:

```yaml
resume_semantics: same-thread | new-run-with-prior-state | unsupported | host-owned
```

Why: LangGraph, Temporal, and Prefect can all run durable work, but they do not expose identical pause/resume semantics. Chatbots and operators need to know whether `resume(thread_id, ...)` truly resumes the same execution, starts a new deployment run with previous state, or delegates the behavior to host code.

## 11. Target Chatbot/Agent Knowledge Access

### What the Chatbot Should Index

High priority:

- `docs/PROJECT_DOSSIER.md`
- `docs/CHATBOT_KNOWLEDGE_BASE.md`
- `docs/IMPROVEMENT_BACKLOG.md`
- `docs/TARGET_ARCHITECTURE.md`
- `README.md`
- `docs/LIBRARIES.md`
- `docs/*.md`
- package READMEs and DESIGN docs
- `src/**/*.py`
- `tests/**/*.py`
- `examples/**/*.py`

Lower priority:

- `pyproject.toml` files for dependencies/extras
- lock files only for dependency audits

Ignore:

- `dist/**`
- caches
- generated package metadata
- duplicate compatibility files unless alias lookup is needed

### Chunk Metadata

Every chunk should include:

```yaml
package: agent | memory | workspace | orchestration | organization | ai | coactra | docs
component: facade | protocol | backend | adapter | domain | test | example | doc
maturity: implemented | reference | experimental | stub | compatibility
statefulness: stateless | process-local | file-backed | sql-backed | external-service-backed
tenant_isolation: none | scope-keyed | path-confined | sql-filtered | policy-gated
public_api: stable | compatibility | internal
extras:
  - sql
  - langgraph
  - a2a
```

### Retrieval Rules for Future Agents

1. Prefer package README/DESIGN plus source file over old compatibility paths.
2. Treat tests as evidence for intended invariants.
3. Do not recommend stub adapters as production implementations.
4. Check `docs/ADAPTER_MATURITY.md` before discussing deployment.
5. Check `docs/STATE_AND_STORAGE.md` before saying something is durable.
6. Check tenant scope files before saying two operations are isolated.

## 12. Suggested Folder Structure

Near-term, keep current package directories to avoid disruptive moves:

```text
library/
  README.md
  docs/LIBRARIES.md
  Makefile
  docs/
    ARCHITECTURE.md
    API_INDEX.md
    ADAPTER_MATURITY.md
    STATE_AND_STORAGE.md
    TENANT_ISOLATION.md
    SECURITY.md
    EXAMPLES.md
    QUICKSTART.md
    INTERFACES.md
    PRODUCTION.md
  examples/
  coactra/
  lib-ai/
  memory/
  workspace/
  orchestration/
  organization/
  agent/
  tests-integration/
  tools/
```

Longer-term, if packaging becomes noisy, consider a `packages/` directory:

```text
library/
  packages/
    coactra/
    coactra-ai/
    coactra-memory/
    coactra-workspace/
    coactra-orchestration/
    coactra-organization/
    coactra-agent/
  docs/
  examples/
  tests-integration/
  tools/
```

Do not do this move until current orchestration package renames settle.

## 13. Migration Plan

### Phase 1: Documentation and Metadata

- Add API index.
- Add adapter maturity registry/docs.
- Add state/storage docs.
- Add tenant isolation docs.
- Add security docs.
- Add indexing ignore manifest.

Outcome: chatbots and humans can answer questions without scanning the entire repo.

### Phase 2: Protocol Completeness Fixes

- Fix `TenantWorkspaceBackendRouter.exec` to forward `ExecOptions`.
- Complete `TenantProcedureStoreRouter`.
- Add router conformance tests.
- Clarify local-only workspace integrations.

Outcome: small correctness gaps are closed without changing public architecture.

### Phase 3: Production Persistence Contracts

- Decide durable approval persistence model.
- Document or implement workflow restart/resume contract.
- Add schema docs and consider migrations.
- Add production A2A verifier guidance.

Outcome: production users understand which state survives restart and which does not.

### Phase 3.5: Runtime Adapter Decision Boundary

- Keep LangGraph as default for agentic procedures and human-in-the-loop checkpointing.
- Keep the implemented Temporal `WorkflowEngine` adapter for hard durable execution, signals, retries, and crash recovery.
- Keep the implemented Prefect `WorkflowEngine` adapter documented as new-run-with-prior-state; deployment-triggered runs are not the same as Temporal signals unless the host flow implements that behavior.
- Keep Coactra `WorkOrder` as the audit ledger regardless of runtime.
- Do not move tenant/org/workspace/memory policy into runtime-specific workflow definitions.

Outcome: Coactra shrinks custom durable-engine behavior behind one adapter contract instead of becoming a runtime.

### Phase 4: Optional Integration Coverage

- Add CI matrix for SQL, LangGraph, A2A, Keycloak mocks, OpenFGA mocks, Graphiti/mem0 as feasible.
- Add local infrastructure examples.

### Phase 5: Public Shell and v1 Readiness

- Freeze preferred import roots in `docs/API_INDEX.md`.
- Add stability tiers for every exported public symbol.
- Add reusable contract tests for public ports.
- Add examples-as-tests for the stable shell.
- Add release/deprecation policy.
- Avoid adding a `Kernel` class until the current composition factories are measured against real examples.

Outcome: the project has a long-lived compatibility story before broadening the surface area.
- Add conformance probes for adapters.

Outcome: optional adapter drift is caught early.

### Phase 5: Compatibility Cleanup

- Publish deprecation timeline.
- Keep compatibility aliases with warnings until one or more minor releases pass.
- Remove or archive stale artifacts such as `.orig` files.

Outcome: public API surface becomes easier to search and support.

## 14. Target Architecture Diagram

```text
+--------------------------------------------------------------------------------+
| Host application                                                               |
| plain functions, service config, composition root                              |
+-----------------------------------+--------------------------------------------+
                                    |
                                    v
+--------------------------------------------------------------------------------+
| coactra-agent                                                                 |
| Agent facade, ports, MCP mount registry, token exchange, collaboration policy  |
+-----------+---------------+----------------+----------------+------------------+
            |               |                |                |
            v               v                v                v
 +----------------+ +----------------+ +----------------+ +----------------------+
 | coactra-ai     | | coactra-memory | | workspace      | | orchestration        |
 | LiteLLM        | | Memory facade  | | desk/backend   | | work + workflow      |
 | Instructor     | | mem0/Graphiti  | | exec policy    | | SQL + LangGraph      |
 | replay store   | | auth/router    | | integrations   | | adapters/promotions  |
 +-------+--------+ +-------+--------+ +-------+--------+ +----------+-----------+
         |                  |                  |                     |
         |                  |                  |                     v
         |                  |                  |          +----------------------+
         |                  |                  |          | organization         |
         |                  |                  |          | org tree/auth/store  |
         |                  |                  |          +----------+-----------+
         |                  |                  |                     |
         v                  v                  v                     v
 LiteLLM APIs       memory engines       filesystem/sandbox      SQL/OpenFGA
 Chroma optional    Neo4j optional       provider backends       tenant routers
```

## 15. Final Recommendation

The cleanest target architecture is close to what already exists. The main work is not a rewrite. It is:

1. Harden the small protocol mismatches.
2. Document state, adapter maturity, tenant isolation, and public APIs.
3. Make local-only integrations explicit or backend-aware.
4. Add optional integration testing.
5. Preserve the current package boundaries and keep `agent` as the composition/policy layer.

This keeps Coactra pragmatic: thin where the ecosystem already has strong engines, custom where the missing layer is genuinely orchestration, policy, tenancy, or state normalization.
