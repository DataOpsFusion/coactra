# Architecture

Coactra should remain a modular Python library suite, not a monolithic agent
framework. The core keeps the policy, tenancy, workspace, memory facade, work
ledger, and integration contracts that are specific to Coactra. Generic durable
execution belongs behind `WorkflowEngine` adapters.

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

Coactra should not grow into a general workflow platform. It ships a small
in-process durable `WorkflowEngine` for the common Procedure path and keeps
LangGraph, Temporal, Prefect, DBOS, or similar runtimes as injectable adapters.

## Research-Backed Decision

The project uses an adopt-first rule for generic infrastructure:

- Coactra's default durable engine is intentionally small: linear Procedure execution, task callbacks, collaborator asks, and approval interrupt/resume.
- LangGraph remains an optional stateful-agent-graph adapter, not a required dependency for the default path.
- Temporal is the first-choice target for hard durable execution and same-thread signal/resume.
- Prefect is useful for Python deployment-triggered workflows, but Coactra must document whether resume is same-thread, host-owned, or a new run carrying prior state.
- PydanticAI is the agent execution runtime behind `coactra.Agent`; pass pydantic-ai `Model` instances or provider strings directly.
- LiteLLM and Instructor remain the right direction for provider normalization and structured output below `coactra[ai]`.

See [../maintainers/roadmap.md](../maintainers/roadmap.md) and [../maintainers/release-policy.md](../maintainers/release-policy.md) for the concrete v1 plan.

## Target Stack

```text
Application functions
  -> coactra[agent] composition root
  -> Coactra policy and state contracts
  -> small default WorkflowEngine where enough
  -> injected runtime adapter where the host needs more
       LangGraph for stateful agent graphs
       Temporal/Prefect/DBOS for durable execution and recovery
  -> external policy/storage engines
       Keycloak, OpenFGA, SQL, Graphiti/mem0, sandbox provider
```

## Package Responsibilities

| Package | Keep owning | Avoid owning |
|---|---|---|
| `coactra` | small app-facing exports and umbrella extras | runtime behavior |
| `coactra[ai]` | model/embedding wrappers, reasoning trace utilities | full agent framework semantics |
| `coactra[memory]` | backend-neutral memory contract | a custom vector/graph memory engine |
| `coactra[workspace]` | desk files, handoff, manifest, local policy | MCP mounting or org policy |
| `coactra[workflow]` | Procedure model, small default engine, work ledger vocabulary | a general workflow platform |
| `coactra[team]` | tenant org tree, permissions, escalation | workflow execution or messaging |
| `coactra[agent]` | composition, tool mount policy, identity, collaboration | sibling package internals |

## Runtime Adoption Rule

Before adding orchestration code, classify it:

1. Coactra-specific policy or boundary: keep it.
2. Portable ledger/state vocabulary: keep it if it improves auditability across runtimes.
3. Generic retries, recovery, scheduling, state replay, or worker orchestration: use a runtime adapter.
4. Framework-specific API ergonomics: hide behind ports until the public API choice is proven.
5. New public vocabulary should be added only when it simplifies current examples more than the existing `Agent` / `Team` / `Workflow` facades.

## Near-Term Migration Shape

```text
WorkOrder / Procedure / Approval / Artifact / Audit
  -> small default WorkflowEngine for Procedure start/resume
  -> optional LangGraph adapter for stateful agent graphs
  -> Temporal/Prefect/DBOS adapters for hard durable workflows
  -> Coactra team/workspace/memory policy remains outside the runtime
```

## Source Anchors

- `docs/concepts/library-map.md` defines the thin-wrapper philosophy and package boundaries.
- `docs/maintainers/agent-design.md` defines ports and composition-root principles.
- `docs/operations/work-orders.md` says work orders are a vocabulary and ledger, not a broker or scheduler.
- `docs/concepts/library-map.md` keeps workspace, agent, and directory responsibilities separate.

## Runtime Factory

`make_workflow_engine()` is the public factory for runtime adapters. `default`
selects Coactra's small durable `WorkflowEngine`; `local` wraps a synchronous
`ProcedureRunner` for tests and prototypes and does not support resume. `langgraph`
currently aliases the small durable engine name for alpha compatibility while the
optional `LangGraphEngine` remains available for graph-backed Procedure runs.
`temporal` builds `TemporalEngine` around a host Temporal client/workflow/task
queue. `prefect` builds `PrefectEngine` around a Prefect deployment runner.

`DurableOrchestrator()` defaults to `make_default_workflow_engine()` when no
engine is injected. Hosts that need hard workflow durability can inject a
Temporal/Prefect/custom `WorkflowEngine` without changing `WorkOrder`,
`Procedure`, approval, org, workspace, or memory concepts.
