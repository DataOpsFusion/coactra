# API Index

This is a human-maintained starter index for public surfaces. Prefer these roots in application code and chatbot answers.

## Stable Package Roots

| Package | Preferred import root | Purpose |
|---|---|---|
| Umbrella | `coactra.scope` | canonical scope conversion DTO |
| Umbrella shell | `coactra.kernel` | beta `Kernel`, `Session`, `Task`, and `TaskResult` shell |
| Umbrella plugins | `coactra.plugins` | beta task lifecycle plugin hooks |
| Umbrella errors | `coactra.errors` | shared `CoactraError` and machine-readable error codes |
| AI | `coactra.ai` | model calls, embeddings, reasoning replay |
| Memory | `coactra.memory` | remember/recall/export facade and backends |
| Workspace | `coactra.workspace` | persistent desk, file/exec policy, workspace backends |
| Work | `coactra.jobs` | durable work orders and work stores |
| Workflow | `coactra.jobs.workflow` | procedure models, runtime protocols, workflow adapters |
| Orchestration | `coactra.jobs` | facade linking work orders and workflows |
| Organization | `coactra.directory` | org tree, persistence, authorization |
| Agent | `coactra.agent` | composition root, ports, MCP/A2A/identity policy |

## Stability Tiers

Use these labels in docs and future generated API metadata:

| Tier | Meaning | Examples today |
|---|---|---|
| stable | preferred public API for application code | package roots, `CoactraScope`, core facades once confirmed by tests |
| beta | public but still settling | runtime factories and some production adapters until contract suites mature |
| experimental | useful but not compatibility-promised | dispatch bridges, MCP task bridges, new runtime adapters |
| compatibility | migration alias, not preferred for new code | `coactra.jobs`, `coactra.jobs.workflow` |
| internal | implementation detail | deep backend internals and helper modules |

See [RELEASE_POLICY.md](RELEASE_POLICY.md) for change rules.

## Current Shell Versus Future Vocabulary

Do not answer future users as if a `Kernel` or unified `Session` API already exists. The current shell is:

| Future concept from research | Current Coactra surface | Guidance |
|---|---|---|
| Kernel | `make_agent`, `make_coactra_agent` | use current factories until repeated examples prove a new class is worth adding |
| Session | agent/workflow/work manager context | not a single public API yet |
| Task | `WorkOrder`, `Procedure`, app function input | keep separate because ledger tasks and reusable procedures are different concepts |
| WorkflowBackend | `WorkflowEngine` | preferred name in current code |

## Important Constructors and Facades

| Name | Import root | Notes |
|---|---|---|
| `CoactraScope` | `coactra.scope` | converts tenant/namespace/agent/session to package kwargs |
| `Kernel` / `Session` | `coactra.kernel` | beta dependency-light root/session shell for function-first task dispatch |
| `Task` / `TaskResult` | `coactra.kernel` | beta task DTOs for the shell; not a replacement for `WorkOrder` |
| `Plugin` / `PluginManager` | `coactra.plugins` | beta task lifecycle hooks: start/end/error |
| `CoactraError` / `ErrorCode` | `coactra.errors` | shared machine-readable error contract |
| `Client` | `coactra.ai` | model client facade |
| `ReasoningEngine` | `coactra.ai` | reasoning trace capture/replay |
| `Memory` | `coactra.memory` | async memory facade with sync bridge |
| `make_backend` | `coactra.memory` | memory backend factory |
| `Workspace` | `coactra.workspace` | scope-bound desk facade |
| `open_workspace` | `coactra.workspace` | workspace factory helper |
| `WorkManager` | `coactra.jobs` | work-order lifecycle service |
| `SqlWorkStore` | `coactra.jobs` | durable SQL work ledger |
| `Procedure` | `coactra.jobs.workflow` | reusable workflow data model |
| `DurableLangGraphEngine` | `coactra.jobs.workflow` | default durable workflow adapter when LangGraph extra is installed |
| `make_workflow_engine` | `coactra.jobs.workflow` | named runtime factory for default/langgraph/local/temporal/prefect |
| `make_default_workflow_engine` | `coactra.jobs.workflow` | constructs the default LangGraph-backed runtime |
| `TemporalEngine` | `coactra.jobs.workflow.adapters` | thin Temporal workflow adapter; requires host client/workflow/task queue |
| `PrefectEngine` | `coactra.jobs.workflow.adapters` | thin Prefect deployment-run adapter; resume is new-run-with-prior-state |
| `Organization` | `coactra.directory` | org tree aggregate |
| `save_org` / `load_org` | `coactra.directory` | explicit org persistence |
| `make_agent` | `coactra.agent` | agent composition root |
| `make_coactra_agent` | `coactra.agent.integrations` | full-stack adapter wiring |

## Compatibility Imports

These exist for migration but should not be preferred in new docs or chatbot answers:

- `coactra.jobs`
- `coactra.jobs.workflow`
- deprecated adapter helpers at `coactra.agent` package root
- older organization store module paths
- workspace `backend.py` / `local.py` compatibility modules

## Index Maintenance Rule

When adding a public class/function:

1. export it from the preferred package root if it is public;
2. add or update a public API test;
3. add it here with purpose and maturity;
4. avoid exposing stub adapters as if they are production implementations.
