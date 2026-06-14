# Basic Incident Triage

The smallest Coactra application: one Team-owned agent that receives an incident description and returns a triage plan.

## Demonstrates

- `team.add_agent(model_capability=..., tools=, instructions=)`
- `agent.run(prompt)`
- plain local tools

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team


def get_runbook(service: str) -> str:
    runbooks = {
        "nginx": "https://wiki.example.com/runbooks/nginx",
        "postgres": "https://wiki.example.com/runbooks/postgres",
    }
    return runbooks.get(service, "https://wiki.example.com/runbooks/generic")


async def triage_incident(incident: str) -> str:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="incident"),
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
        name="triage-1",
        auth="dev-token",
        tools=[get_runbook],
        instructions="You are a senior SRE. Be brief and actionable.",
    )
    return await agent.run(f"Triage this incident: {incident}")
```
