# Support Desk

A helpdesk agent that drafts answers with automatic memory. The runnable part combines `Team` + `Agent` + memory.

## Demonstrates (Runnable)

- `team.add_agent(model_capability=..., memory=..., tools=, instructions=)`
- Automatic recall of prior tickets per customer
- Local tools for ticket resolution

## Code (Runnable)

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team


def fetch_ticket(ticket_id: str) -> dict:
    return {"id": ticket_id, "subject": "Can't log in", "status": "open"}


def mark_resolved(ticket_id: str, resolution: str) -> str:
    return f"Ticket {ticket_id} marked resolved: {resolution}"


async def handle_ticket(ticket_id: str, customer_id: str) -> str:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="support"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="support-desk",
                profile=ModelProfile(
                    name="support-desk",
                    model="openai/qwen3.6-plus",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    agent = await team.add_agent(
        model_capability="support-desk",
        name="support-desk",
        auth="dev-token",
        memory="inprocess",
        tools=[fetch_ticket, mark_resolved],
        instructions=(
            "You are a tier-1 support agent. Recall past issues, draft a clear "
            "resolution, and mark the ticket resolved when done."
        ),
    )
    return await agent.run(f"Handle ticket {ticket_id} for customer {customer_id}")
```

## Workflow Extension

```python
from coactra import Workflow
from coactra.workflow import step

play = Workflow("support-ticket", steps=[
    step("fetch and draft resolution", agent="support-desk"),
    step("manager approval", approve=True),
    step("mark resolved", agent="support-desk"),
])
await team.run(play)
```
