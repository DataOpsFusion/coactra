# API Index

Coactra 0.0.x alpha public application surface.

## Top-Level Exports

```python
from coactra import (
    Agent, CoactraError, Decision, DecisionOutcome, ErrorCode,
    MissingExtraError, Policy, PolicyRequest, RemotePeer, Run,
    Scope, Skill, StaticToken, Team, ValidationError, Workflow, __version__,
)
```

## Stable app-facing blocks

| Name | Description |
|------|-------------|
| `Agent` | One-agent facade. Use `Agent.create(...)` for the lazy path. |
| `Team` | Coordination root for agents, skills, workflows, policy, and model defaults. |
| `Skill` | Curated capability metadata for routing/discovery. |
| `Scope` | Tenant/session boundary. |
| `Policy` / `PolicyRequest` / `Decision` | Governance hook. |
| `Workflow` | Playbook runner for routed steps. |
| `RemotePeer` | Remote A2A peer config. |
| `Run` | Async run handle. |

## Lazy constructors

```python
agent = await Agent.create(model="openai:gpt-4.1-mini")

team = Team.local(model="openai:gpt-4.1-mini", tenant_id="acme")
agent = await team.add_agent("triage")
smart = await team.add_agent("smart", model="anthropic:claude-sonnet-4")
```

## Named routes

```python
team.add_model("senior", "anthropic:claude-sonnet-4")
senior = await team.add_agent("senior", model_capability="senior")
```

## CLI

```bash
coactra doctor
coactra init triage-bot
coactra validate team.json
```

Advanced host/runtime seams live in explicit submodules such as `coactra.model`,
`coactra.workflow.ledger`, and `coactra.team.directory`.

Removed alpha roots are intentionally not compatibility-shimmed; the exact banned names are enforced by the architecture guard and release checklist.
