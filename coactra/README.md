# coactra

Composable orchestration blocks for agentic systems. Coactra gives you small primitives —
`Agent`, `Team`, `Skill`, `Policy`, `Scope`, `Memory`, `Workspace`, and `Workflow` — plus lazy
builders so you write less glue code.

```bash
pip install "coactra[agent]"
```

## One agent

```python
import asyncio
from coactra import Agent

async def main() -> None:
    agent = await Agent.create(model="openai:gpt-4.1-mini")
    try:
        print(await agent.run("Triage nginx 502s on checkout"))
    finally:
        await agent.aclose()

asyncio.run(main())
```

## Local team

```python
from coactra import Skill, Team

team = Team.local(model="openai:gpt-4.1-mini", tenant_id="acme")
triage = await team.add_agent("triage", skills=[Skill("incident")])
reviewer = await team.add_agent("reviewer", model="anthropic:claude-sonnet-4")
```

## Named model routes without boilerplate

```python
team = Team.local(model="openai:gpt-4.1-mini", tenant_id="acme")
team.add_model("senior", "anthropic:claude-sonnet-4")
senior = await team.add_agent("senior-reviewer", model_capability="senior")
```

`model_capability=` is now only the named-route selector. Users should not need to construct
route/profile objects in normal app code.

## CLI

```bash
coactra doctor
coactra init triage-bot
coactra validate team.json
```

## Public surface

```python
from coactra import Agent, Team, Scope, Policy, Skill, Workflow
from coactra.workflow import step
```

Advanced internals remain in explicit submodules for host/runtime authors.
