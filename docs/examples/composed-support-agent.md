# Composed Support Agent

A support agent with multiple local tools and a structured `Skill` roster so it can be discovered by a Team.

## Demonstrates

- `team.add_agent(model_capability=..., tools=, skills=, memory=, instructions=)`
- `Skill(id, description, tags, scopes)`
- `agent.card`
- Multiple local tools passed as a plain list

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team


def search_knowledge_base(query: str) -> list[str]:
    return [f"Article: How to fix '{query}'"]


def escalate_ticket(ticket_id: str, reason: str) -> str:
    return f"Ticket {ticket_id} escalated: {reason}"


def update_ticket_status(ticket_id: str, status: str) -> str:
    return f"Ticket {ticket_id} set to {status}"


async def build_support_agent():
    team = Team(
        scope=Scope(tenant_id="acme", namespace="support"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="tier1-support",
                profile=ModelProfile(
                    name="tier1-support",
                    model="openai/qwen3.6-plus",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    return await team.add_agent(
        model_capability="tier1-support",
        name="tier1-support",
        auth="dev-token",
        tools=[search_knowledge_base, escalate_ticket, update_ticket_status],
        memory="inprocess",
        skills=[
            Skill(
                "support",
                description="Handle tier-1 customer support tickets",
                tags=["helpdesk", "tier1"],
                scopes=["tickets:read", "tickets:write"],
            )
        ],
        instructions=(
            "You are a tier-1 support agent. Search the KB first, then resolve "
            "or escalate. Always update the ticket status."
        ),
        expose=True,
    )
```
