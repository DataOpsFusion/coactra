# Support Desk

A helpdesk agent that drafts answers with automatic memory. The runnable part
combines `Agent` + memory. Durable work tracking and approval pauses are part of
the **Workflow** layer — see the badge below.

## Demonstrates (Runnable)

- `Agent.create(model=, memory=, tools=, instructions=)`
- Automatic recall of prior tickets per customer
- Local tools for ticket resolution

## Code (Runnable)

```python
import asyncio
from coactra import Agent


def fetch_ticket(ticket_id: str) -> dict:
    """Stub: look up a ticket from your ticketing system."""
    return {"id": ticket_id, "subject": "Can't log in", "status": "open"}


def mark_resolved(ticket_id: str, resolution: str) -> str:
    """Stub: mark a ticket resolved."""
    return f"Ticket {ticket_id} marked resolved: {resolution}"


async def handle_ticket(ticket_id: str, customer_id: str) -> str:
    agent = await Agent.create(
        model="claude-sonnet-4-5",
        name="support-desk",
        tenant="acme",
        auth="dev-token",
        memory="inprocess",     # swap to "graphiti" or "mem0" in production
        tools=[fetch_ticket, mark_resolved],
        instructions=(
            "You are a tier-1 support agent. Recall past issues, draft a clear "
            "resolution, and mark the ticket resolved when done."
        ),
    )
    return await agent.run(
        f"Handle ticket {ticket_id} for customer {customer_id}"
    )


if __name__ == "__main__":
    print(asyncio.run(handle_ticket("TKT-1001", "cust-42")))
```

## Workflow Extension

Use `Workflow` when ticket handling needs durable approval pause/resume:

```python
from coactra import Workflow
from coactra.workflow import step

play = Workflow("support-ticket", steps=[
    step("fetch and draft resolution", agent="support-desk"),
    step("manager approval", approve=True),
    step("mark resolved", agent="support-desk"),
])
await play.run(team)
```

## Production Notes

| Concern | Dev default | Production |
|---|---|---|
| Auth | `auth="dev-token"` | `StaticToken` or authlib/httpx-oauth `TokenSource` |
| Memory backend | `"inprocess"` | `"graphiti"` or `"mem0"` |
| Tool access | local functions | `gateway="https://gateway/mcp"` + `auth=` |
