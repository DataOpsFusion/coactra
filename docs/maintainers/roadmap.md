# Roadmap To v1

This roadmap converts the framework research into a Coactra-specific plan. The goal is a long-lived thin orchestration library, not a new all-in-one agent framework.

## Product Verdict

Keep building Coactra only where it has a durable domain advantage:

- scope and tenant semantics
- organization policy and authorization boundaries
- workspace desk and execution policy
- durable work-order ledger, approvals, artifacts, and audit vocabulary
- backend-neutral memory and reasoning seams
- agent composition above MCP, A2A, identity, and capability ports

Do not rebuild commodity runtime features:

- generic model/provider routing
- structured output validation and retries
- graph checkpoint storage
- replay/retry/recovery engines
- job scheduling and worker infrastructure
- broad plugin management before hooks are proven

## Adopt-First Decisions

| Concern | Decision | Coactra boundary |
|---|---|---|
| Stateful agent procedures | LangGraph remains the default `WorkflowEngine` target | Coactra owns `Procedure`, `RunContext`, scope, interrupts, and work-ledger mapping. LangGraph owns graph execution and checkpointing. |
| Hard durable execution | Temporal is the first serious replacement for custom durable-engine behavior | Coactra owns payload shape, work-order audit, tenant policy, and adapter contract. Temporal owns workflow history, retries, signals, replay, and workers. |
| Pythonic deployment workflows | Prefect is a secondary adapter target | Coactra can trigger deployment runs and pass state/decision payloads. Same-thread resume must be host-implemented or clearly marked unsupported. |
| Typed agent API inspiration | Use PydanticAI as a reference, not an immediate rewrite | Borrow typed deps/tools/output patterns only where they simplify `coactra.agent` and `coactra.ai`. |
| Provider normalization | Keep LiteLLM and Instructor behind `coactra.ai` | Coactra should expose a stable model/structured-output seam, not provider-specific details. |
| Plugin system | Defer broad plugins; consider pluggy if hooks become real public API | Start with a tiny hook list and contract tests before advertising ecosystem plugins. |

## Current Public Shell

The research suggests a `Kernel` / `Session` / `Scope` / `Task` model. Coactra should not add that vocabulary blindly. Today the equivalent public shell is:

| Target concept | Current Coactra surface | Status |
|---|---|---|
| Scope | `coactra.scope.CoactraScope` plus package-local `Scope` DTOs | keep and document as stable first |
| Kernel / composition root | `coactra.kernel.Kernel`, `coactra.agent.make_agent`, `coactra.agent.integrations.make_coactra_agent` | `Kernel` is a beta function/task shell; agent factories remain the AI-agent composition roots |
| Session | `coactra.kernel.Session` plus agent/workflow/work manager context objects | beta umbrella session exists for task dispatch; durable runtime sessions still belong to their packages |
| Task | `coactra.kernel.Task`, `WorkOrder`, `Procedure`, and app functions | keep separate because shell dispatch, ledger work, and reusable procedures differ |
| Workflow backend | `WorkflowEngine` | keep small; add contract tests and resume-semantics metadata |
| Ports | agent/memory/workspace/workflow/org Protocols | keep; add reusable conformance suites |

## Stability Tiers Before v1

Every exported symbol should be assigned one tier:

| Tier | Meaning | Change rule |
|---|---|---|
| stable | preferred public API for application code | no breaking change without deprecation window |
| beta | public but may still change before v1 | breaking changes allowed with changelog and migration note |
| experimental | useful but not compatibility-promised | may change or be removed between minor releases |
| compatibility | old import path or migration alias | keep until documented removal window closes |
| internal | not for application imports | can change anytime |

## Milestones

### v0.1 - Public Inventory

Deliverables:

- generated or maintained public API inventory
- stability tier for each exported public symbol
- compatibility alias manifest
- adapter maturity manifest with resume semantics

Exit criteria:

- a chatbot can answer "what should I import?" from `docs/API_INDEX.md`
- no stub adapter is described as production-ready
- every compatibility import has a preferred replacement

### v0.2 - Stable Shell Examples

Deliverables:

- examples that use only preferred imports
- docs for `CoactraScope`, `make_agent`, `make_coactra_agent`, `WorkManager`, `DurableOrchestrator`, `WorkflowEngine`, `Memory`, `Workspace`, and `Organization`
- examples-as-tests for the stable shell

Exit criteria:

- a new app can be built without deep imports
- examples state which backends are local/reference versus production-ready

### v0.3 - Port Contract Tests

Deliverables:

- reusable conformance suites for `MemoryBackend`, `WorkspaceBackend`, `WorkStore`, `ProcedureStore`, `WorkflowEngine`, `OrgStore`, and agent ports
- router conformance tests that verify every protocol method is forwarded
- optional-extra test lane definitions

Exit criteria:

- each implemented adapter passes its port contract
- tenant routers cannot drift from the protocols unnoticed

### v0.4 - Runtime Adapter Boundary

Deliverables:

- LangGraph default runtime documented with restart/checkpointer requirements
- Temporal adapter boundary implemented and backed by fake-client unit tests
- Prefect adapter boundary implemented as new-run-with-prior-state and backed by fake-runner unit tests
- runtime adapter payload schema documented

Exit criteria:

- custom durable-engine behavior is behind `WorkflowEngine`
- `WorkOrder` remains the durable business ledger across all runtime choices
- `resume_semantics` is documented for every runtime adapter

### v0.5 - Production Persistence Contracts

Deliverables:

- durable approval persistence decision
- work and org schema docs or migrations
- state/storage matrix updated with restart guarantees
- production A2A verifier requirements

Exit criteria:

- operators can tell what survives process restart
- approval/input pauses are not process-memory-only unless explicitly documented

### v0.6 - Provider And Typed Output Boundary

Deliverables:

- documented provider-normalization policy for `coactra.ai`
- typed structured-output contract inspired by PydanticAI/Instructor where useful
- error model that maps provider/runtime/storage failures into Coactra domain errors

Exit criteria:

- provider-specific responses do not leak across the stable shell
- retryability and user-visible failure categories are machine-readable

### v0.7 - Optional Plugins Or Hooks

Deliverables:

- tiny beta hookspec list in `coactra.plugins`
- hook ordering and error-isolation tests
- no ad hoc callbacks in examples unless they are marked experimental

Exit criteria:

- extension points are intentional public contracts
- plugins do not become a second hidden orchestration framework
- new hooks are not added without public API tests and docs

### v0.8 - Integration And Operations

Deliverables:

- local integration environment templates for Postgres, Neo4j/Graphiti, Keycloak, OpenFGA, and optional runtime dependencies
- CI matrix for core, SQL, LangGraph, A2A, memory engines, and auth mocks
- smoke tests for optional extras

Exit criteria:

- contributors can reproduce production-ish seams locally
- optional adapters fail in CI before users find dependency drift

### v0.9 - Security And Performance

Deliverables:

- secret handling guide
- workspace path and local exec hardening checklist
- tenant router lifecycle/eviction strategy
- thin-layer overhead benchmarks

Exit criteria:

- no production guide relies on token passthrough
- high-tenant deployments have a cleanup/close strategy
- public claims about being thin have measured support

### v1.0 - Compatibility Freeze

Deliverables:

- stable import roots frozen
- deprecation/removal policy published
- changelog grouped by added/changed/deprecated/removed/fixed/security
- v1 examples run in CI

Exit criteria:

- stable shell can remain compatible across minor releases
- beta/experimental surfaces are clearly separated from stable application APIs

## Immediate Work Order

1. Finish public API inventory and stability tiers.
2. Add `resume_semantics` to adapter maturity metadata.
3. Add conformance suites for the existing ports before adding more adapters.
4. Add real Temporal service integration coverage for the adapter payload and signal contract.
5. Add real Prefect deployment integration coverage for the new-run-with-prior-state pattern.
6. Document LangGraph restart requirements with a persistent checkpointer.
7. Make every example list prototype backends and production replacements.
8. Add release/deprecation policy and compatibility alias manifest.
9. Add optional-extra CI matrix definitions.
10. Only then evaluate whether a `Kernel` class is useful.
