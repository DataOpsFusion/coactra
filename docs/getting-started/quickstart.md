# Quickstart

This guide builds a small incident-triage agent using the current public API. Start from the root package and add lower-level backends only when the app needs them.

`Agent` is a thin composition shell over pydantic-ai. For advanced model control, pass a pydantic-ai `Model` instance directly. `Team` and `Workflow` are the multi-agent orchestration layer.

## 1. Install

```bash
pip install "coactra[agent]"
```

For source development:

```bash
python -m pip install -e "./coactra[all,dev]"
```

## 2. Write A Tool

A tool is just a callable. Coactra adapts it for the model runtime.

```python
def get_runbook(service: str) -> str:
    runbooks = {
        "nginx": "https://wiki.example.com/runbooks/nginx",
        "postgres": "https://wiki.example.com/runbooks/postgres",
    }
    return runbooks.get(service, "https://wiki.example.com/runbooks/generic")
```

## 3. Create An Agent

```python
import asyncio
from coactra import Agent, Skill


def get_runbook(service: str) -> str:
    return f"https://wiki.example.com/runbooks/{service}"


async def main() -> None:
    agent = await Agent.create(
        model="anthropic:claude-haiku-4-5",
        name="triage-agent",
        tenant="acme",
        auth="dev-token",
        tools=[get_runbook],
        skills=[Skill(id="incident.triage", description="Triage production incidents")],
        instructions="You are a senior SRE. Be concise and actionable.",
    )
    answer = await agent.run("Triage nginx 502s on checkout")
    print(answer)


asyncio.run(main())
```

For full provider control, pass a pydantic-ai model instance:

```python
from pydantic_ai.models.anthropic import AnthropicModel

agent = await Agent.create(
    model=AnthropicModel("claude-haiku-4-5"),
    ...
)
```

## 4. Add Memory, Workspace, Or Gateway Tools

```python
from coactra import Agent, StaticToken

agent = await Agent.create(
    model="anthropic:claude-sonnet-4-5",
    name="sre-agent",
    tenant="acme",
    gateway="https://gateway.example/mcp",
    auth=StaticToken("your-gateway-token"),  # or any async TokenSource
    memory="graphiti",
    workspace="./desk",
)
```

For OAuth client-credentials fetch and refresh, use `authlib` or `httpx-oauth` and pass the resulting token source to `auth=`. Coactra ships `StaticToken` for dev and pre-fetched production tokens.

## 5. Route Across A Team

```python
from coactra import Agent, Skill, Team

security = await Agent.create(
    model="anthropic:claude-haiku-4-5",
    name="security-agent",
    tenant="acme",
    auth="dev-token",
    skills=[Skill(id="security.review", description="Review security-sensitive changes")],
)
team = Team([security])
print(team.match("review certificate rotation risk").card)
```

## 6. Run A Workflow

```python
from coactra import Workflow
from coactra.workflow import step

workflow = Workflow(
    "cert rotation",
    steps=[
        step("plan", needs="sre planning"),
        step("approve", needs="security review", approve=True),
        step("execute", needs="sre execution"),
    ],
)
```

`Workflow` supports Team capability routing, approval pause/resume, checkpoint storage, and swappable engine seams.

## 7. Production Shape

| Concern | Development | Production |
|---|---|---|
| Auth | `auth="dev-token"` | `StaticToken` or custom `TokenSource` (authlib / httpx-oauth for client-credentials) |
| Model | provider string (`anthropic:...`) | pydantic-ai `Model` instance with explicit provider config |
| Tools | local callables | `gateway=` plus scoped auth |
| Memory | in-process or named local backend | Graphiti/mem0 adapter with tenant scope |
| Workspace | local gated directory | host-controlled workspace backend |
| Peers | local `Agent` objects | `RemotePeer(...)` over A2A (`coactra.agent.adapters`) |
| Inbound A2A | not required for local dev | wire `a2a-sdk` server; handler calls `await agent.run(message)` |

Coactra should give you stable seams. Keep business behavior in plain functions and let `Agent`, `Team`, and `Workflow` own runtime state.
