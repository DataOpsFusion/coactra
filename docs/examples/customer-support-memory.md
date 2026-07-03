# Customer Support Memory

An agent that automatically remembers and recalls past support interactions.

## Demonstrates

- `team.add_agent(memory="graphiti", model_capability=...)`
- Memory is auto-injected into the model's context
- `memory="inprocess"` for local/offline development

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team


async def handle_ticket(ticket_text: str, customer_id: str) -> str:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="support"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="support-memory",
                profile=ModelProfile(
                    name="support-memory",
                    model="openai/deepseek-v4-pro",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    agent = await team.add_agent(
        model_capability="support-memory",
        name="support-agent",
        auth="dev-token",
        memory="inprocess",
        instructions=(
            "You are a helpful support agent. Use past interactions to give "
            "consistent, personalised answers."
        ),
    )
    return await agent.run(f"[customer:{customer_id}] {ticket_text}")
```

## Production Swap

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, StaticToken, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="support"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="support-memory",
            profile=ModelProfile(
                name="support-memory",
                model="openai/deepseek-v4-pro",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    model_capability="support-memory",
    name="support-agent",
    auth=StaticToken("gateway-token"),
    gateway="https://gateway/mcp",
    memory="graphiti",
    instructions="...",
)
```
