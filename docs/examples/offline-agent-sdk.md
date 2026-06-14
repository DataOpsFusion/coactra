# Offline Agent SDK

Create an agent with local tools and stream its events — no network model required.

## Demonstrates

- `team.add_agent(model_capability=..., tools=, instructions=)`
- `agent.send(prompt).stream()`
- offline model substitution through `ModelResolver`

## Code

```python
import asyncio

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team


def check_disk(host: str) -> dict:
    return {"host": host, "used_pct": 78, "free_gb": 22}


def restart_service(host: str, service: str) -> str:
    return f"Restarted {service} on {host}"


def offline_model(messages, info):
    return ModelResponse(parts=[TextPart("disk is fine; no restart needed")])


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="offline"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="offline-sre",
                profile=ModelProfile(name="offline-sre", model=FunctionModel(offline_model)),
            )
        ]),
    )
    agent = await team.add_agent(
        model_capability="offline-sre",
        name="sre-agent",
        auth="dev-token",
        tools=[check_disk, restart_service],
        instructions="You are an SRE agent. Check before you act.",
    )

    print("Streaming response:")
    async for event in agent.send("Check disk on web-01 and restart nginx if >80%").stream():
        print(event)
```
