# Architecture

Coactra should remain a modular Python library suite, not a monolithic agent framework. The durable runtime should be delegated to mature engines where possible; Coactra should keep the policy, tenancy, workspace, memory facade, work ledger, and integration contracts that are specific to this project.

## Positioning

Coactra owns the cross-capability shell:

- tenant and scope conventions
- agent composition and ports
- MCP mount timing and tool naming policy
- delegated identity and no-token-passthrough invariants
- A2A collaboration policy gates
- workspace desk and execution policy
- memory backend neutrality
- work-order vocabulary, audit state, approvals, artifacts, and budgets
- organization hierarchy, permissions, escalation, and authorization seams

Coactra should not grow into a general durable workflow engine. Runtime execution should be wrapped through adapters to LangGraph, Temporal, Prefect, DBOS, or similar backends.

## Research-Backed Decision

The project should use an adopt-first rule for generic infrastructure:

- LangGraph is the default stateful agent procedure runtime.
- Temporal is the first-choice target for hard durable execution and same-thread signal/resume.
- Prefect is useful for Python deployment-triggered workflows, but Coactra must document whether resume is same-thread, host-owned, or a new run carrying prior state.
- PydanticAI is a useful API-design reference for typed dependencies, tools, and structured output, but adopting its vocabulary should not force a rewrite of Coactra's package model.
- LiteLLM and Instructor remain the right direction for provider normalization and structured output below `coactra.ai` (`pip install "coactra[ai]"`).

See [../maintainers/roadmap.md](../maintainers/roadmap.md) and [../maintainers/release-policy.md](../maintainers/release-policy.md) for the concrete v1 plan.

## Target Stack

```text
Application functions
  -> coactra.agent composition root (make_agent)
  -> Coactra policy and state contracts
  -> runtime adapter where needed
       LangGraph as the default agentic stateful execution adapter
       Temporal/Prefect/DBOS for durable execution and recovery
  -> external policy/storage engines
       Keycloak, OpenFGA, SQL, Graphiti/mem0, sandbox provider
```

## Capability Responsibilities

One PyPI distribution (`coactra`); capabilities are modules plus optional extras.

| Module | Extra (typical) | Keep owning | Avoid owning |
|---|---|---|---|
| `coactra.scope` | — | shared `CoactraScope` | runtime behavior |
| `coactra.ai` | `[ai]` | model/embedding wrappers, reasoning trace utilities | full agent framework semantics |
| `coactra.memory` | `[memory]` + backend extras | backend-neutral memory contract | a custom vector/graph memory engine |
| `coactra.workspace` | — | desk files, handoff, manifest, local policy | MCP mounting or org policy |
| `coactra.jobs` | base + `[sql]`, `[langgraph]`, … | durable work ledger and procedure model | broker/scheduler/workflow engine replacement |
| `coactra.jobs.workflow` | `[langgraph]`, `[temporal]`, … | procedure DSL and engine adapters | custom durable engine beyond adapters/gates |
| `coactra.directory` | `[organization]` | tenant org tree, permissions, escalation | workflow execution or messaging |
| `coactra.agent` | `[agent]` | composition, tool mount policy, identity, collaboration | capability module internals |

## Runtime Adoption Rule

Before adding orchestration code, classify it:

1. Coactra-specific policy or boundary: keep it.
2. Portable ledger/state vocabulary: keep it if it improves auditability across runtimes.
3. Generic retries, recovery, scheduling, state replay, or worker orchestration: use a runtime adapter.
4. Framework-specific API ergonomics: hide behind ports until the public API choice is proven.
5. New public vocabulary such as `Kernel`, `Session`, or `Task`: add only when it simplifies current examples more than the existing factories and facades.

## Near-Term Migration Shape

```text
WorkOrder / Procedure / Approval / Artifact / Audit
  -> LangGraph adapter for stateful agent graphs
  -> Temporal/Prefect/DBOS adapters for durable workflows
  -> Coactra organization/workspace/memory policy remains outside the runtime
```

## Source Anchors

- `docs/concepts/library-map.md` defines the thin-wrapper philosophy and package boundaries.
- `docs/maintainers/agent-design.md` defines ports and composition-root principles.
- `docs/operations/work-orders.md` says work orders are a vocabulary and ledger, not a broker or scheduler.
- `docs/concepts/library-map.md` keeps workspace, agent, and directory responsibilities separate.

## Runtime Factory

`make_workflow_engine()` is the public factory for runtime adapters. `default` and `langgraph` select the checkpointed LangGraph adapter. `local` wraps a synchronous `ProcedureRunner` for tests and prototypes and does not support resume. `temporal` builds `TemporalEngine` around a host Temporal client/workflow/task queue. `prefect` builds `PrefectEngine` around a Prefect deployment runner.

`DurableOrchestrator()` now defaults to `make_default_workflow_engine()` when no engine is injected. Hosts that need hard workflow durability can still inject a Temporal/Prefect/custom `WorkflowEngine` without changing `WorkOrder`, `Procedure`, approval, org, workspace, or memory concepts. Temporal provides same-thread signal/resume semantics; Prefect resume is modeled as a new deployment run carrying prior state unless the host flow implements stricter behavior.
