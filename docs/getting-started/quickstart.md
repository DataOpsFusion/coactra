# Quickstart

This guide builds a small incident-triage system using the Team-first public API. `Team` is the assembly door; `Agent` remains the runtime actor type returned by `team.add_agent(...)`.

## 1. Install

```bash
pip install "coactra[agent]"
```

For source development:

```bash
python -m pip install -e "./coactra[all,dev]"
```

## 2. Write A Tool

```python
def get_runbook(service: str) -> str:
    runbooks = {
        "nginx": "https://wiki.example.com/runbooks/nginx",
        "postgres": "https://wiki.example.com/runbooks/postgres",
    }
    return runbooks.get(service, "https://wiki.example.com/runbooks/generic")
```

## 3. Create A Team And Add An Agent

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team


def get_runbook(service: str) -> str:
    return f"https://wiki.example.com/runbooks/{service}"


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="support"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="triage",
                profile=ModelProfile(
                    name="triage",
                    model="openai/qwen3.6-plus",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    agent = await team.add_agent(
        model_capability="triage",
        name="triage-agent",
        auth="dev-token",
        tools=[get_runbook],
        skills=[Skill(id="incident.triage", description="Triage production incidents")],
        instructions="You are a senior SRE. Be concise and actionable.",
        expose=True,
    )
    answer = await agent.run("Triage nginx 502s on checkout")
    print(answer)


asyncio.run(main())
```

For deterministic local tests, route a capability to `TestModel()` or `FunctionModel(...)` instead of a live provider.

## 4. Add Memory, Workspace, Or Gateway Tools

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, StaticToken, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="ops"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="sre",
            profile=ModelProfile(
                name="sre",
                model="openai/qwen3.6-plus",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    model_capability="sre",
    name="sre-agent",
    gateway="https://gateway.example/mcp",
    auth=StaticToken("your-gateway-token"),
    memory="graphiti",
    workspace="./desk",
)
```

## 5. Route Across A Team

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="security"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="security-review",
            profile=ModelProfile(
                name="security-review",
                model="openai/qwen3.6-plus",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
await team.add_agent(
    model_capability="security-review",
    name="security-agent",
    auth="dev-token",
    skills=[Skill(id="security.review", description="Review security-sensitive changes")],
    expose=True,
)
print(team.match_skill("security.review").card)
```

## 6. Run A Workflow

```python
from coactra import Workflow
from coactra.workflow import step

workflow = Workflow(
    "cert rotation",
    steps=[
        step("plan", requires_skill="sre.plan"),
        step("approve", requires_skill="security.review", approve=True),
        step("execute", requires_skill="sre.execute"),
    ],
)
```

`Workflow` supports Team skill routing, approval pause/resume, checkpoint storage, and swappable engine seams.

## 7. Production Shape

| Concern | Development | Production |
|---|---|---|
| Policy | `Policy.permissive()` | guarded / approval-gated custom policy |
| Scope | `Scope(tenant_id="acme", namespace="support")` | tenant/workspace-qualified scope |
| Model | `TestModel()` / `FunctionModel(...)` route | Team-owned routed profiles via `ModelResolver` |
| Tools | local callables | `gateway=` plus scoped auth |
| Memory | in-process or named local backend | Graphiti/mem0 adapter with tenant scope |
| Workspace | local gated directory | host-controlled workspace backend |
| Peers | local runtime agents | `RemotePeer(...)` over A2A |

Coactra should give you stable seams. Keep business behavior in plain functions and let `Team`, `Agent`, and `Workflow` own runtime state.
