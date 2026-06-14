# Quickstart

Coactra is a block kit, not a monolith. Start tiny, then replace defaults when you need more control.

## Install

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

## One team

```python
from coactra import Skill, Team

team = Team.local(model="openai:gpt-4.1-mini", tenant_id="acme", namespace="support")
triage = await team.add_agent(
    "triage-agent",
    skills=[Skill("incident", description="Triage production incidents")],
    instructions="Be concise and actionable.",
    expose=True,
)
```

## Two models

```python
fast = await team.add_agent("fast-agent")
smart = await team.add_agent("smart-agent", model="anthropic:claude-sonnet-4")
```

## Named route

```python
team.add_model("senior", "anthropic:claude-sonnet-4")
senior = await team.add_agent("senior-reviewer", model_capability="senior")
```

## Tools, memory, workspace, gateway

```python
from coactra import StaticToken

def get_runbook(service: str) -> str:
    return f"https://wiki.example.com/runbooks/{service}"

agent = await team.add_agent(
    "sre-agent",
    tools=[get_runbook],
    gateway="https://gateway.example/mcp",
    auth=StaticToken("dev-token"),
    memory="inprocess",
    workspace="./desk",
)
```

Use explicit `Policy` and `Scope` when you are building a host/runtime boundary; use lazy builders for app code.
