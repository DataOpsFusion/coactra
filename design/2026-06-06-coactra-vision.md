# Coactra — System Vision

**Status:** current Team-first alpha architecture.

Coactra is a component-based orchestration fabric for agentic systems. It is
not a new model SDK, memory store, workflow engine, or enterprise IAM system.
It is the coordination, policy, and adapter layer that makes those ecosystems
work together under one governed execution model.

## Core stance

- Coactra owns composition, scope propagation, policy checks, execution records, and adapter contracts.
- External systems own provider normalization, memory storage, workflow durability, transport protocols, and host authentication.
- Every serious action is scoped, governed, and observable.

## Main public nouns

- `Team` — the assembly and coordination root
- `Agent` — a runtime actor owned by a Team or host
- `Workflow` — a reusable process definition and execution facade
- `Skill` — a packaged capability advertised and routed by id
- `Scope` — the execution address
- `Policy` / `Decision` — the enforcement seam
- `Run` — the execution record

## Team-first execution model

The public assembly door is `Team`, not a standalone agent factory.

```python
from coactra import Policy, Scope, Team, Workflow

team = Team(
    scope=Scope.local(),
    policy=Policy.permissive(),
)
agent = await team.add_agent(name="sre-agent", model_capability="fast-chat")
run = await team.run(Workflow("deploy", steps=[...]))
```

`Agent` remains a thin runtime shell over pydantic-ai, but it is constructed
through `Team.add_agent(...)` in the current alpha contract.

## Component map

- `Team` owns agent registration, skill catalogs, workflow catalogs, policy defaults, and routing.
- `Agent` reasons, requests models, uses assigned skills, calls tools, and delegates under Team policy.
- `Workflow` binds steps to exact `requires_skill` ids or explicit `agent=` overrides.
- `Memory` is an adapter-backed capability, not a standalone product.
- `Workspace` is an adapter-backed capability, not a standalone product.
- `ModelResolver` chooses governed model routes.
- Adapters connect Coactra contracts to LiteLLM, Pydantic AI, LangGraph, mem0, Graphiti, MCP, A2A, Temporal, and OpenFGA.

## Public philosophy

- Few public nouns
- Strong internal model
- One execution path
- No hidden permissionless mode
- Team defines and assigns
- Agent acts
- Workflow defines process
- Policy governs before side effects
- Adapters are replaceable and do not define Coactra's identity

## What Coactra avoids

- building a new provider SDK abstraction from scratch
- building a new durable workflow engine
- building a memory database
- inventing a new tool protocol
- exposing enterprise directory internals as first-class app nouns

## Current reference docs

- `design/2026-06-06-agent-api-design.md` — current Agent runtime contract
- `design/2026-06-06-team-design.md` — Team-first coordination contract
- `design/2026-06-06-workflow-design.md` — capability-routed workflow contract
- `design/2026-06-06-auth-design.md` — gateway, token, and policy seam
- `design/2026-06-06-review-refinements.md` — boundary and hardening refinements
- `design/2026-06-09-team-first-alpha-work-orders.md` — migration/build order record
- `design/IMPLEMENTATION_STATUS.md` — current implementation audit
