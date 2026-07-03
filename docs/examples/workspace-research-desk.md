# Workspace Research Desk

An agent with a **workspace** — a persistent desk where it can read and write files between tasks and sessions.

## Demonstrates

- `team.add_agent(workspace="./desk", model_capability=...)`
- Workspace surfaces as tools the model can call directly
- `run` is allow-listed
- Persistent notes across sessions

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team


async def research_session(topic: str) -> str:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="research"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="research",
                profile=ModelProfile(
                    name="research",
                    model="openai/deepseek-v4-pro",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    agent = await team.add_agent(
        model_capability="research",
        name="research-agent",
        auth="dev-token",
        workspace="./desk",
        instructions=(
            "You are a research assistant. Use the workspace to take notes, "
            "store findings, and write a summary file when done."
        ),
    )
    return await agent.run(f"Research {topic} and save a summary to summary.md")
```
