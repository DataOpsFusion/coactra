# Improvement Backlog

This backlog is based on static source inspection and later architecture-alignment passes. It separates observed facts from recommendations.

## Strategic Updates From Framework Research

### 0. Freeze the public shell before adding more surface area

- Status: Roadmap docs added; enforcement still pending.
- Problem: the research proposes useful `Kernel` / `Session` / `Task` vocabulary, but the repo already has partial equivalents through `CoactraScope`, `make_agent`, `make_coactra_agent`, `WorkManager`, `Procedure`, `DurableOrchestrator`, and `WorkflowEngine`. Adding new nouns too early would widen the public API before the current shell is classified.
- Evidence from files:
  - Current preferred imports are listed in `docs/API_INDEX.md`.
  - Interface map prefers package roots and function-first app code in `docs/INTERFACES.md:1-42`.
  - Agent composition roots exist in `agent/src/coactra/agent/factory.py` and `agent/src/coactra/agent/integrations/factory.py`.
- Why it matters: a thin orchestration library lives or dies by compatibility discipline. A broad public shell creates more breaking-change debt than value.
- Recommended fix: assign stability tiers to exported symbols, add a compatibility alias manifest, and keep `Kernel` as a future concept until examples prove it removes real wiring complexity.
- Difficulty: Medium
- Priority: P1

### 0.1. Add release policy and v1 roadmap gates

- Status: Initial docs added in `docs/RELEASE_POLICY.md` and `docs/ROADMAP_V1.md`; generated enforcement is pending.
- Problem: package boundaries are clear, but compatibility promises, deprecation windows, and adapter maturity are not yet tied to release gates.
- Evidence from files:
  - Package versions differ across `*/pyproject.toml`.
  - Compatibility aliases are documented in `orchestration/README.md:72-78` and `docs/API_INDEX.md`.
- Why it matters: users and chatbot agents need to know which imports are stable, beta, experimental, compatibility, or internal.
- Recommended fix: keep `docs/RELEASE_POLICY.md` as source of truth, add API diff checks later, and require changelog categories for public changes.
- Difficulty: Low
- Priority: P1

### 0.2. Make runtime resume semantics explicit

- Status: Roadmap and maturity docs updated; adapter metadata/enforcement pending.
- Problem: LangGraph, Temporal, and Prefect can all run durable workflows, but `resume(thread_id, ...)` does not mean the same thing unless the adapter declares its semantics.
- Evidence from files:
  - `WorkflowEngine.start/resume` protocol in `orchestration/src/coactra/orchestration/workflow/runtime/durable.py:50-80`.
  - Runtime factory names LangGraph, Temporal, and Prefect in `orchestration/src/coactra/orchestration/workflow/runtime/defaults.py`.
  - Current adapter maturity doc now defines `same-thread`, `new-run-with-prior-state`, `unsupported`, and `host-owned`.
- Why it matters: operators may assume Temporal-like signal/resume behavior from adapters that only trigger a new run or delegate resume to host code.
- Recommended fix: keep `resume_semantics` in the machine-readable adapter manifest and add real-service integration tests for Temporal and Prefect behind the same `WorkflowEngine` contract.
- Difficulty: Medium
- Priority: P1

### 0.3. Add port conformance suites before expanding adapters

- Status: Some package-specific conformance tests exist; cross-port coverage is incomplete.
- Problem: the research correctly emphasizes contract testing. Coactra has many Protocol seams, but not every adapter/router has a reusable conformance suite.
- Evidence from files:
  - Existing memory conformance in `memory/src/coactra/memory/conformance.py`.
  - Existing work conformance in `orchestration/src/coactra/orchestration/work/conformance.py`.
  - Agent conformance in `agent/src/coactra/agent/conformance.py`.
  - Router drift was already found in workspace and procedure routers.
- Why it matters: adapter drift is the main failure mode of a thin library suite.
- Recommended fix: add reusable suites for `WorkflowEngine`, `WorkspaceBackend`, `ProcedureStore`, `OrgStore`, tenant routers, and agent ports.
- Difficulty: Medium
- Priority: P1

### 0.4. Treat PydanticAI as an API reference, not a rewrite trigger

- Problem: PydanticAI's typed dependencies, tools, outputs, and durable execution integrations are relevant, but replacing Coactra's domain model with another framework would erase the project-specific value.
- Evidence from files:
  - Coactra's project-specific boundaries are documented in `LIBRARIES.md:27-91`.
  - Agent ports and dependency injection are defined in `agent/DESIGN.md:11-23`.
- Why it matters: the best path is selective adoption of typed patterns where they simplify Coactra's API, not a framework migration that narrows the product scope by accident.
- Recommended fix: create one spike comparing a simple Coactra agent flow to a PydanticAI-style typed-deps flow, then adopt only the parts that reduce API noise.
- Difficulty: Medium
- Priority: P2

## Critical Fixes

### 1. Forward workspace execution options through the tenant router

- Status: Implemented in the first architecture-alignment pass.
- Problem: `TenantWorkspaceBackendRouter.exec` accepts only `command` and `scope`, while the backend protocol and local backend support `ExecOptions`.
- Evidence from files:
  - `WorkspaceBackend.exec(command, scope, options=None)` is defined in `workspace/src/coactra/workspace/backends/base.py:48-54`.
  - `LocalFilesystemBackend.exec(command, scope, options=None)` implements cwd/env/timeout/output bounds in `workspace/src/coactra/workspace/backends/local.py:75-122`.
  - `TenantWorkspaceBackendRouter.exec(self, command, scope)` omits options in `workspace/src/coactra/workspace/routing.py:43-44`.
  - Existing router test only checks tenant separation, not `ExecOptions`, in `workspace/tests/test_routing.py:10-26`.
- Why it matters: tenant-routed workspaces silently lose execution configuration, which can break timeouts, cwd, env, and output controls in production.
- Recommended fix: change router signature to accept `options: ExecOptions | None = None` and forward it. Add a router test that passes an options object and asserts the selected backend receives it.
- Difficulty: Low
- Priority: P1

### 2. Make `TenantProcedureStoreRouter` satisfy the full `ProcedureStore` protocol

- Status: Implemented in the first architecture-alignment pass.
- Problem: `ProcedureStore` includes `exists`, `replace`, and `delete`, but the tenant router exposes only `save`, `get`, and `list`.
- Evidence from files:
  - `ProcedureStore` protocol in `orchestration/src/coactra/orchestration/workflow/store.py:16-40`.
  - `TenantProcedureStoreRouter` in `orchestration/src/coactra/orchestration/workflow/routing.py:13-22`.
- Why it matters: code using the router as a `ProcedureStore` can fail at runtime for valid protocol methods.
- Recommended fix: add `exists`, `replace`, and `delete` forwarding methods. Add protocol conformance and behavior tests.
- Difficulty: Low
- Priority: P1

### 3. Provide durable approval storage or clearly mark approval persistence as host-owned

- Problem: reusable workflow approval storage is in-memory, while production docs mention persisted approvals as a production seam.
- Evidence from files:
  - `InMemoryApprovalStore` is the only approval store found in `orchestration/src/coactra/orchestration/workflow/runtime/approval.py:46-81`.
  - `DurableOrchestrator` maps approval interrupts into work order approval state in `orchestration/src/coactra/orchestration/facade.py:280-332`.
  - README names "persisted approvals" as a production seam in `README.md:15-17`.
- Why it matters: approval state that only exists in memory can be lost across process restart unless the host maps it into durable work state consistently.
- Recommended fix: either add a SQL-backed `ApprovalStore` or document the exact host contract: approval state is persisted through `WorkOrder.pending_approval`, not `InMemoryApprovalStore`. Add restart/resume tests around approval flows.
- Difficulty: Medium
- Priority: P1

### 4. Make workspace integrations backend-aware or mark them local-only

- Problem: some workspace integrations bypass `WorkspaceBackend` and use direct `Path` operations.
- Evidence from files:
  - `distill_journal` uses local `Path` reads/writes and `.distilled` markers in `workspace/src/coactra/workspace/integrations/memory.py:21-31` and `workspace/src/coactra/workspace/integrations/memory.py:55-75`.
  - `propose_candidate_workflow` writes YAML files through `Path.write_text` in `workspace/src/coactra/workspace/integrations/workflow.py:41-47`.
  - Workspace design says Daytona/E2B/OpenHands are intended backend seams, not local-only desks, in `workspace/README.md:29-40`.
- Why it matters: direct filesystem access will not work for remote/sandbox backends and makes the integration boundary misleading.
- Recommended fix: move these operations through the `Workspace` facade/backend where possible. If a raw host path is required, rename functions or docs to say "local workspace only".
- Difficulty: Medium
- Priority: P1

## Architecture Improvements

### 5. Add a machine-readable adapter maturity registry

- Problem: adapter maturity is spread across `LIBRARIES.md`, package READMEs, docstrings, and stub tests.
- Evidence from files:
  - Adapter maturity matrix in `LIBRARIES.md:187-195`.
  - Workspace adapter maturity mapping in `workspace/src/coactra/workspace/adapters/__init__.py:1-17`.
  - Agent FastMCP stub in `agent/src/coactra/agent/adapters/fastmcp.py:1-12`.
  - Organization Neo4j stub in `organization/src/coactra/organization/repository/neo4j_store.py:1-14`.
  - `TemporalEngine` and `PrefectEngine` in `orchestration/src/coactra/orchestration/workflow/adapters/temporal.py` and `orchestration/src/coactra/orchestration/workflow/adapters/prefect.py`; resume semantics now differ by runtime.
- Why it matters: chatbots and users can easily confuse named seams with implemented production backends.
- Recommended fix: add `docs/ADAPTER_MATURITY.md` plus a small JSON/YAML manifest listing adapter, package, extra, maturity, dependency, production status, and replacement path.
- Difficulty: Low
- Priority: P1

### 6. Clarify durable LangGraph restart and resume requirements

- Problem: durable workflow resume depends on checkpointer/thread state and procedure availability. The engine stores thread-to-procedure mapping in memory and raises if procedure is not available after restart.
- Evidence from files:
  - Scoped thread IDs and snapshots in `orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py:809-840`.
  - Resume behavior and missing-procedure error path in `orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py:843-944`.
  - `WorkflowEngine.start/resume` protocol in `orchestration/src/coactra/orchestration/workflow/runtime/durable.py:50-80`.
- Why it matters: users may assume "durable" means restart-safe without knowing what must be persisted by the host.
- Recommended fix: document required durable inputs: checkpointer, thread id, workflow document/procedure version, work order checkpoint, pending approval/input state. Add a restart simulation test if feasible.
- Difficulty: Medium
- Priority: P1

### 7. Decide whether `AsyncPostgresOrgStore` should be native async or explicitly thread-backed

- Problem: the name implies native async Postgres, but implementation wraps the synchronous SQL repository and forwards work through `asyncio.to_thread`.
- Evidence from files:
  - Thread-backed async facade described in `organization/src/coactra/organization/repository/async_store.py:1-6`.
  - Dynamic async forwards in `organization/src/coactra/organization/repository/async_store.py:32-69`.
- Why it matters: host services may make incorrect assumptions about connection pooling, transaction behavior, and async DB driver requirements.
- Recommended fix: either rename to `AsyncThreadedOrgStore`/`AsyncSqlOrgStore`, or implement a native async SQLAlchemy/Postgres store. At minimum, document the current behavior in `organization/README.md`.
- Difficulty: Medium
- Priority: P2

### 8. Keep `agent` as the only cross-capability composition layer

- Problem: as integrations grow, memory/workspace/workflow/org can accidentally start importing each other or owning behavior outside their boundaries.
- Evidence from files:
  - `LIBRARIES.md:70-91` defines boundaries: workflow owns when/what, organization owns who, agent carries talk, memory and reasoning stores are separate.
  - `agent/DESIGN.md:11-23` locks ports and DI.
  - Workspace README says agent owns MCP mounting and organization owns hierarchy/policy (`workspace/README.md:33-40`).
- Why it matters: preserving clean package boundaries is the main architectural strength of the project.
- Recommended fix: add boundary tests or lint checks that prevent sibling imports outside `integrations/`. Add `docs/BOUNDARIES.md`.
- Difficulty: Medium
- Priority: P2

## Code Cleanup

### 9. Reduce deprecated compatibility noise in chatbot indexes

- Problem: compatibility modules and root-level deprecated exports create duplicate APIs for retrieval.
- Evidence from files:
  - `coactra.work` and `coactra.workflow` compatibility aliases documented in `orchestration/README.md:72-78`.
  - Agent root deprecated lookup map in `agent/src/coactra/agent/__init__.py:114-145`.
  - Organization compatibility imports in `organization/README.md:47-51`.
  - Workspace compatibility imports in `workspace/README.md:76-77`.
- Why it matters: a chatbot may answer with old import paths unless aliases are tagged.
- Recommended fix: create a compatibility manifest with preferred import path, alias path, deprecation status, and removal horizon. Use it in docs and retrieval metadata.
- Difficulty: Low
- Priority: P2

### 10. Remove or explain `organization/src/coactra/organization/__init__.py.orig`

- Problem: `.orig` source file appears in the repo inventory.
- Evidence from files:
  - `organization/src/coactra/organization/__init__.py.orig` appears in `rg --files`.
- Why it matters: backup/original files are confusing for package readers and chatbots.
- Recommended fix: inspect whether it is needed. If not, remove it in a separate cleanup change. If it is intentional, move it under docs or test fixtures and explain it.
- Difficulty: Low
- Priority: P2

### 11. Align package versioning or document independent version policy

- Problem: package versions are mixed: several are `0.2.0`, while `workspace`, `orchestration`, and umbrella are `0.1.0`.
- Evidence from files:
  - `lib-ai/pyproject.toml:5-33`
  - `memory/pyproject.toml:5-29`
  - `organization/pyproject.toml:5-29`
  - `agent/pyproject.toml:5-45`
  - `workspace/pyproject.toml:5-41`
  - `orchestration/pyproject.toml:5-47`
  - `coactra/pyproject.toml:5-32`
- Why it matters: users need to know whether versions move independently or as a coordinated suite.
- Recommended fix: add `docs/RELEASE_POLICY.md` explaining package versioning, compatibility aliases, and extras.
- Difficulty: Low
- Priority: P2

## Documentation Improvements

### 12. Generate an API index from public exports and Protocols

- Problem: public API roots exist, but there is no single API inventory for humans or chatbots.
- Evidence from files:
  - `docs/INTERFACES.md:20-31` lists stable roots.
  - Package `__init__.py` files export many names, such as `agent/src/coactra/agent/__init__.py:64-112` and `orchestration/src/coactra/orchestration/__init__.py:36-64`.
- Why it matters: retrieval and onboarding improve when public names have one canonical source.
- Recommended fix: generate `docs/API_INDEX.md` grouped by package, class/function, source file, public/compat/internal status, and one-line purpose.
- Difficulty: Low
- Priority: P1

### 13. Add state and storage documentation

- Problem: persistent state is spread across SQL store code, SQLModel models, workspace files, memory backends, and in-memory caches.
- Evidence from files:
  - Work tables in `orchestration/src/coactra/orchestration/work/backends/sql.py:96-138`.
  - Org tables in `organization/src/coactra/organization/models.py:46-163`.
  - Workspace storage in `workspace/src/coactra/workspace/backends/local.py:24-122`.
  - Memory backends in `memory/src/coactra/memory/backends/`.
  - Agent token cache in `agent/src/coactra/agent/identity.py:148-205`.
- Why it matters: production operators need to know what survives restart and what is process-local.
- Recommended fix: create `docs/STATE_AND_STORAGE.md` with persistence class, backend, durability, tenant isolation, cleanup/backup strategy, and secrets notes.
- Difficulty: Medium
- Priority: P1

### 14. Add tenant isolation documentation

- Problem: every package has scope semantics, but there is no one tenant isolation doc.
- Evidence from files:
  - `CoactraScope` conversions in `coactra/src/coactra/scope.py:26-98`.
  - Memory scope key behavior in `memory/src/coactra/memory/types.py:24-87`.
  - Workspace path-safe scope in `workspace/src/coactra/workspace/scope.py:15-32`.
  - Collaboration cross-tenant denial in `agent/src/coactra/agent/collaboration.py:52-79`.
  - Organization tenant isolation in `organization/DESIGN.md:69-76`.
- Why it matters: tenant isolation is a selling point and a security boundary.
- Recommended fix: create `docs/TENANT_ISOLATION.md` with per-package semantics, cross-tenant denial, router usage, and known limitations.
- Difficulty: Low
- Priority: P1

### 15. Document "local only" versus "production-ready" examples

- Problem: examples use in-process/local defaults by design, but users may copy them into production.
- Evidence from files:
  - Examples README says examples use in-process/local defaults and replace backend boundary for production (`examples/projects/README.md:12`).
  - `docs/QUICKSTART.md:101-112` shows replacing `WorkManager` storage with SQL.
- Why it matters: examples should be safe to copy without hidden production assumptions.
- Recommended fix: add a short "production replacements" block to each example README: memory backend, workspace backend, work store, org store, A2A verifier, token exchanger.
- Difficulty: Low
- Priority: P2

## Testing Improvements

### 16. Add optional extras CI matrix

- Problem: many important paths depend on optional extras and may skip locally.
- Evidence from files:
  - Optional extras in `orchestration/pyproject.toml:17-47`, `agent/pyproject.toml:17-45`, `memory/pyproject.toml:15-29`, `workspace/pyproject.toml:15-41`.
  - Live memory tests are environment-gated in `memory/tests/test_live_integration.py:1-60`.
- Why it matters: adapter drift is likely when tests do not run with real optional dependencies.
- Recommended fix: add CI jobs for core, SQL, LangGraph, A2A, memory engines, org SQL/OpenFGA mocks, workspace integrations. Keep live external service jobs separately gated.
- Difficulty: High
- Priority: P1

### 17. Add router conformance tests

- Problem: router classes are simple but can drift from protocols, as seen with workspace and procedure routers.
- Evidence from files:
  - Router files: `lib-ai/src/coactra/ai/routing.py`, `memory/src/coactra/memory/routing.py`, `workspace/src/coactra/workspace/routing.py`, `orchestration/src/coactra/orchestration/workflow/routing.py`, `organization/src/coactra/organization/repository/routing.py`, `agent/src/coactra/agent/routing.py`.
- Why it matters: routers are used for tenant silo deployments, where missing methods become production runtime failures.
- Recommended fix: for each router, create a fake backend that records all protocol calls and assert every protocol method forwards scope and options correctly.
- Difficulty: Medium
- Priority: P1

### 18. Add restart/resume tests for durable workflows

- Problem: durable workflow engine has rich resume behavior but restart assumptions are subtle.
- Evidence from files:
  - Durable runtime protocol in `orchestration/src/coactra/orchestration/workflow/runtime/durable.py:50-80`.
  - Durable LangGraph state and resume code in `orchestration/src/coactra/orchestration/workflow/backends/durable_langgraph.py:676-944`.
- Why it matters: "durable" is only meaningful if restart behavior is well tested or clearly scoped.
- Recommended fix: simulate engine restart with persisted checkpointer and procedure/version reload. Assert expected behavior for pending interrupt, approval resolution, and missing procedure.
- Difficulty: High
- Priority: P2

### 19. Add non-local workspace backend contract tests

- Problem: workspace integrations may not work beyond local filesystem.
- Evidence from files:
  - Local direct path usage in `workspace/src/coactra/workspace/integrations/memory.py` and `workspace/src/coactra/workspace/integrations/workflow.py`.
  - Workspace backend protocol in `workspace/src/coactra/workspace/backends/base.py`.
- Why it matters: sandbox backends are part of the design vision.
- Recommended fix: create an in-memory fake backend and run desk/integration tests against it. This catches direct `Path` assumptions.
- Difficulty: Medium
- Priority: P2

## Security Improvements

### 20. Add a secrets and credentials guide

- Problem: production docs warn about secrets, but there is no complete guide for tokens, workspace manifests, memory, and logs.
- Evidence from files:
  - Secret warning in `docs/PRODUCTION.md:82-90`.
  - Keycloak token exchange code in `agent/src/coactra/agent/adapters/keycloak.py:102-262`.
  - Workspace manifest and handoff behavior in `workspace/src/coactra/workspace/desk.py:32-174`.
  - Memory persistence backends in `memory/src/coactra/memory/backends/`.
- Why it matters: agents can accidentally persist sensitive tokens or prompts in workspace/memory.
- Recommended fix: add `docs/SECURITY.md` with rules for bearer tokens, workspace files, memory events, audit logs, A2A headers, Keycloak config, and local exec.
- Difficulty: Medium
- Priority: P1

### 21. Harden token cache lifecycle

- Problem: `CachedAsyncTokenExchanger` caches exchanged identities in-process by TTL but has no explicit invalidation or max size.
- Evidence from files:
  - Cache implementation in `agent/src/coactra/agent/identity.py:148-205`.
- Why it matters: long-running services may need logout/revocation handling, bounded memory use, and audit visibility.
- Recommended fix: add optional max size, explicit invalidate methods, and metrics hooks. Document that it is a convenience cache, not an authorization source of truth.
- Difficulty: Medium
- Priority: P2

### 22. Make A2A inbound verifier requirements explicit

- Problem: inbound A2A app supports a verifier, but without one the host handler receives requests without auth checks.
- Evidence from files:
  - `verifier` is optional in `make_a2a_executor` and `build_a2a_app` (`agent/src/coactra/agent/adapters/a2a_server.py:104-199`).
- Why it matters: production A2A services must not expose unchecked capabilities.
- Recommended fix: production docs should require a verifier and allowed subject prefixes. Optionally add `build_production_a2a_app` that requires verifier explicitly.
- Difficulty: Low
- Priority: P1

## Performance Improvements

### 23. Add bounded cache/eviction strategy to tenant routers

- Problem: tenant routers cache one backend/runtime per tenant and have no eviction/close lifecycle.
- Evidence from files:
  - `TenantReasoningStoreRouter` cache in `lib-ai/src/coactra/ai/routing.py:10-31`.
  - `TenantMemoryBackendRouter` cache in `memory/src/coactra/memory/routing.py:12-43`.
  - `TenantWorkspaceBackendRouter` cache in `workspace/src/coactra/workspace/routing.py:11-44`.
  - `TenantAgentRouter` cache in `agent/src/coactra/agent/routing.py:10-24`.
- Why it matters: high-tenant-count services can leak backend clients, filesystem handles, or external connections.
- Recommended fix: add optional LRU/TTL eviction and `close()` hooks where backends support cleanup.
- Difficulty: Medium
- Priority: P2

### 24. Clarify Graphiti export limitations and add pagination if possible

- Problem: Graphiti `dump` uses a broad empty-query search and is not a full export.
- Evidence from files:
  - `GraphitiBackend.dump` in `memory/src/coactra/memory/backends/graphiti.py:357-361`.
  - Export is lossy by design in `memory/src/coactra/memory/export.py:1-9`.
- Why it matters: users may assume migration/export captures all facts and edges.
- Recommended fix: document as approximate. If Graphiti exposes a native full export/page API, implement it behind capability metadata.
- Difficulty: Medium
- Priority: P2

## Search/RAG Improvements

### 25. Add front matter metadata to docs

- Problem: docs are readable but not machine-labeled by package, maturity, statefulness, or public API status.
- Evidence from files:
  - Current docs are plain Markdown: `README.md`, `LIBRARIES.md`, `docs/*.md`, package READMEs/DESIGNs.
- Why it matters: retrieval quality improves when chunks can be filtered.
- Recommended fix: add YAML front matter with `package`, `role`, `maturity`, `statefulness`, `extras`, `public_api`, and `tenant_isolation` fields.
- Difficulty: Low
- Priority: P2

### 26. Split long design documents into stable knowledge chunks

- Problem: `LIBRARIES.md` and package design files contain dense cross-cutting decisions that could retrieve too broadly.
- Evidence from files:
  - `LIBRARIES.md` covers philosophy, tenancy, package boundaries, dependency shape, adapter maturity, and compatibility aliases.
  - `agent/DESIGN.md`, `organization/DESIGN.md`, and package READMEs contain multiple concepts per file.
- Why it matters: smaller chunks reduce hallucinated cross-package ownership.
- Recommended fix: generate or maintain `docs/kb/*.md` chunk files from the knowledge base in this report.
- Difficulty: Low
- Priority: P2

### 27. Add an ignore manifest for chatbot indexing

- Problem: generated files and compatibility aliases can pollute retrieval.
- Evidence from files:
  - `dist/`, `.pytest_cache/`, `.ruff_cache/`, `uv.lock`, compatibility modules, and `.orig` file appear in the repo inventory.
- Why it matters: a chatbot may prefer generated/stale/duplicate files over source of truth.
- Recommended fix: add `docs/INDEXING.md` or `.coactra-indexignore` with include/exclude patterns and rationale.
- Difficulty: Low
- Priority: P2

## Developer Experience Improvements

### 28. Add local integration environment templates

- Problem: no Docker/Compose/env example files were found for optional service dependencies such as Postgres, Neo4j, Keycloak, or OpenFGA.
- Evidence from files:
  - `rg --files` inventory found no Docker/Compose/env examples.
  - Package docs reference Postgres, Neo4j, Keycloak, and OpenFGA configuration through examples or constructors.
- Why it matters: contributors cannot easily reproduce integration paths.
- Recommended fix: add `examples/infra/compose.yaml` or separate docs for local Postgres, Neo4j, Keycloak, OpenFGA. Keep secrets in `.env.example`, not real env files.
- Difficulty: Medium
- Priority: P2

### 29. Add package-local verification shortcuts

- Problem: top-level Makefile runs all package tests, but package-local development often needs targeted commands.
- Evidence from files:
  - `Makefile:1-10` only defines `test` and `test-core`.
- Why it matters: contributors need fast checks for one package or one optional extra.
- Recommended fix: add documented commands like `make test PKG_DIR=memory` or package-local task runner scripts if desired. Avoid disrupting current Makefile behavior.
- Difficulty: Low
- Priority: P3

### 30. Add source-generated diagrams

- Problem: architecture is currently prose-heavy.
- Evidence from files:
  - `LIBRARIES.md`, `docs/INTERFACES.md`, and package READMEs explain relationships but have limited diagrams.
- Why it matters: package boundaries and data flows are easier for humans and chatbots with diagrams.
- Recommended fix: add Mermaid or ASCII diagrams for package dependency graph, work lifecycle, memory flow, workspace flow, agent policy flow, and org permission resolution.
- Difficulty: Low
- Priority: P3

## Summary Priority Order

1. P1: Freeze the public shell, stability tiers, and compatibility alias policy.
2. P1: Add runtime `resume_semantics` metadata and enforce it in adapter docs/tests.
3. P1: Fix workspace router `ExecOptions` forwarding.
4. P1: Complete `TenantProcedureStoreRouter`.
5. P1: Clarify or implement durable approval persistence.
6. P1: Make workspace integrations backend-aware or label local-only.
7. P1: Add adapter maturity, API index, state/storage, tenant isolation, security, release, and v1 roadmap docs.
8. P1: Add optional extras CI and port/router conformance tests.
9. P2: Add real-service integration tests for Temporal and Prefect behind the `WorkflowEngine` adapter boundary.
10. P2: Clarify durable LangGraph restart/resume and async org store behavior.
11. P2: Improve examples, indexing metadata, tenant router lifecycle, and integration environment setup.
