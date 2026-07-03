# Library Map

Coactra is one Python distribution with a small root API and optional capability
extras. The public promise is not "one more agent framework"; it is a
policy-aware composition library for AI workloads.

## Installation

```bash
pip install coactra
pip install "coactra[agent]"
pip install "coactra[memory,workflow]"
pip install "coactra[all]"
```

Base install stays dependency-light. Extras add runtime or backend packages only
when a host application asks for them.

## Public Shape

Start from:

```python
from coactra import Scope, Policy, Team, Skill, Workflow, step
```

The root vocabulary is intentionally tiny:

| Concept | Job |
|---|---|
| `Scope` | tenant, namespace, agent, and session identity |
| `Policy` / `PolicyRequest` | actor/action/resource/scope decisions |
| `Team` | composition root for agents, skills, workflows, model routes, and policy |
| `Agent` | thin runtime facade over pydantic-ai |
| `Skill` | discovery metadata for routing and A2A Agent Cards |
| `Workflow` / `step` | authored playbooks and approval-capable runs |

## Capability Boundaries

| Module / extra | Owns | Does not own |
|---|---|---|
| `coactra[memory]` | backend-neutral recall/write/export contracts | embeddings, vector engines, graph engines |
| `coactra[workspace]` | persistent desk/files/manifest/local policy | sandbox provider implementation |
| `coactra[workflow]` | procedure DTOs, work ledger, approvals, runtime adapter contracts | durable engine replacement |
| `coactra[team]` | tenant directory and authorization seams | workflow execution or messaging |
| `coactra[agent]` | composition, pydantic-ai runtime, MCP tools, A2A delegation policy | model-provider SDK replacement |

If LangGraph, Temporal, Prefect, Graphiti, mem0, LlamaIndex, MCP, A2A, or a host
runtime already owns the engine, Coactra wraps lightly or accepts a user-supplied
object. It should not clone the engine.

## Dependency Shape

```text
coactra core: Scope + Policy + Model routes
        |
        +-- memory       (optional backends)
        +-- workspace    (desk/files)
        +-- workflow     (procedures + ledger + adapters)
        +-- team         (directory/authorization)
        |
        +-- agent        (Team-built runtime composition)
```

Capability modules should stay independently useful. Cross-module wiring belongs
in explicit integration seams or in `Team.add_agent(...)`.

## Removed Alpha Surfaces

These were cut because they made Coactra own too much:

- `coactra.ai`
- semantic skill matching and embedding helpers
- learned-procedure replay on `Team.add_agent(...)`
- `Workflow.run_goal(...)` model-planned workflows
- workflow induction and promotion helpers

Hosts can still build those behaviors explicitly with their chosen model runtime,
memory engine, and workflow engine. Coactra should provide the policy and wiring
surface, not the speculative brain.
