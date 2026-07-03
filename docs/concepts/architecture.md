# Architecture

Coactra should remain a policy-aware composition library for AI workloads, not an
agent framework, memory framework, or workflow engine. Host applications keep
their model, memory, tool, and runtime choices; Coactra keeps the policy,
tenancy, scope, workspace, work-ledger, and adapter contracts between them.

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
- team hierarchy, permissions, escalation, and authorization seams

Coactra should not grow into a general durable workflow engine. Runtime execution should be wrapped through adapters to LangGraph, Temporal, Prefect, DBOS, or similar backends.

## Research-Backed Decision

The project should use an adopt-first rule for generic infrastructure:

- LangGraph is a supported stateful procedure adapter.
- Temporal is the first-choice target for hard durable execution and same-thread signal/resume.
- Prefect is useful for Python deployment-triggered workflows, but Coactra must document whether resume is same-thread, host-owned, or a new run carrying prior state.
- PydanticAI is the agent execution runtime behind `coactra.Agent`; pass pydantic-ai `Model` instances or provider strings directly.

See [../maintainers/roadmap.md](../maintainers/roadmap.md) and [../maintainers/release-policy.md](../maintainers/release-policy.md) for the concrete v1 plan.

## Target Stack

```text
Application functions
  -> coactra[agent] composition root
  -> Coactra policy and state contracts
  -> runtime adapter where needed
       LangGraph as a stateful execution adapter
       Temporal/Prefect/DBOS for durable execution and recovery
  -> external policy/storage engines
       Keycloak, OpenFGA, SQL, Graphiti/mem0, sandbox provider
```

## Package Responsibilities

| Package | Keep owning | Avoid owning |
|---|---|---|
| `coactra` | shared `Scope` and umbrella extras | runtime behavior |
| `coactra[memory]` | backend-neutral memory contract | a custom vector/graph memory engine |
| `coactra[workspace]` | desk files, handoff, manifest, local policy | MCP mounting or org policy |
| `coactra[workflow]` | durable business ledger vocabulary | broker/scheduler/workflow engine replacement |
| `coactra[workflow]` | procedure data model and engine adapters | custom durable engine beyond adapters/gates |
| `coactra[team]` | tenant org tree, permissions, escalation | workflow execution or messaging |
| `coactra[agent]` | composition, tool mount policy, identity, collaboration | sibling package internals |

## Runtime Adoption Rule

Before adding orchestration code, classify it:

1. Coactra-specific policy or boundary: keep it.
2. Portable ledger/state vocabulary: keep it if it improves auditability across runtimes.
3. Generic retries, recovery, scheduling, state replay, or worker orchestration: use a runtime adapter.
4. Framework-specific API ergonomics: hide behind ports until the public API choice is proven.
5. New public vocabulary should be added only when it simplifies current examples more than the existing Agent / Team / Workflow facades.

## Near-Term Migration Shape

```text
WorkOrder / Procedure / Approval / Artifact / Audit
  -> LangGraph adapter for stateful agent graphs
  -> Temporal/Prefect/DBOS adapters for durable workflows
  -> Coactra team/workspace/memory policy remains outside the runtime
```

## Source Anchors

- `docs/concepts/library-map.md` defines the thin-wrapper philosophy and package boundaries.
- `docs/maintainers/agent-design.md` defines ports and composition-root principles.
- `docs/operations/work-orders.md` says work orders are a vocabulary and ledger, not a broker or scheduler.
- `docs/concepts/library-map.md` keeps workspace, agent, and directory responsibilities separate.

## Runtime Factory

`make_workflow_engine()` is the public factory for runtime adapters. `default` and `langgraph` select the checkpointed LangGraph adapter. `local` wraps a synchronous `ProcedureRunner` for tests and prototypes and does not support resume. `temporal` builds `TemporalEngine` around a host Temporal client/workflow/task queue. `prefect` builds `PrefectEngine` around a Prefect deployment runner.

`DurableOrchestrator()` uses the configured runtime adapter when one is supplied. Hosts that need hard workflow durability can inject a Temporal/Prefect/custom `WorkflowEngine` without changing `WorkOrder`, `Procedure`, approval, org, workspace, or memory concepts. Temporal provides same-thread signal/resume semantics; Prefect resume is modeled as a new deployment run carrying prior state unless the host flow implements stricter behavior.
