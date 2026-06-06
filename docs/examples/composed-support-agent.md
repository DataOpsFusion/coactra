# Composed Support Agent

A support agent with multiple local tools and a structured `Skill` roster so it
can be discovered by a Team. This replaces the old "ports + composition root"
pattern — in the new model, composition is `Agent.create(tools=[...], skills=[...])`.

## Demonstrates

- `Agent.create(tools=, skills=, memory=, instructions=)`
- `Skill(id, description, tags, scopes)` — structured capability roster entry
- `agent.card` — the published Agent Card (curated, no raw tool schemas)
- Multiple local tools passed as a plain list

## Code

```python
import asyncio
from coactra import Agent, Skill


# --- Local tools (plain Python functions) ---

def search_knowledge_base(query: str) -> list[str]:
    """Search internal KB articles."""
    # stub — wire to your real KB
    return [f"Article: How to fix '{query}'"]


def escalate_ticket(ticket_id: str, reason: str) -> str:
    """Escalate a ticket to tier-2."""
    return f"Ticket {ticket_id} escalated: {reason}"


def update_ticket_status(ticket_id: str, status: str) -> str:
    """Update ticket status."""
    return f"Ticket {ticket_id} set to {status}"


# --- Agent ---

async def build_support_agent() -> "Agent":
    return await Agent.create(
        model="claude-sonnet-4-5",
        name="tier1-support",
        tenant="acme",
        token="dev-token",
        tools=[search_knowledge_base, escalate_ticket, update_ticket_status],
        memory="inprocess",
        skills=[
            Skill(
                "support.tier1",
                description="Handle tier-1 customer support tickets",
                tags=["support", "helpdesk"],
                scopes=["tickets:read", "tickets:write"],
            )
        ],
        instructions=(
            "You are a tier-1 support agent. Search the KB first, then resolve "
            "or escalate. Always update the ticket status."
        ),
    )


async def triage_incident(incident_text: str) -> str:
    agent = await build_support_agent()
    return await agent.run(incident_text)


if __name__ == "__main__":
    result = asyncio.run(triage_incident("TKT-9001: user can't reset password"))
    print(result)
```

## Agent Card

`agent.card` exposes the curated skills roster — the blurb peers and Team routing
use for capability discovery. Raw tool names and argument schemas are **never**
published.

```python
print(agent.card)
# → {"name": "tier1-support", "tenant": "acme",
#    "skills": [{"id": "support.tier1", "description": "...", ...}]}
```

## Production Notes

| Concern | Dev default | Production |
|---|---|---|
| Auth | `token="dev-token"` | `auth=oidc(issuer, client_id, client_secret)` |
| MCP tools | local functions | `gateway="https://gateway/mcp"` + `auth=` |
| Memory | `"inprocess"` | `"graphiti"` or `"mem0"` |
