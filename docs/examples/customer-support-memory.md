# Customer Support Memory

An agent that **automatically remembers and recalls** past support interactions.
Memory is a named capability — set `memory="graphiti"` and the agent handles
recall and storage without extra code.

## Demonstrates

- `Agent.create(memory="graphiti")` — automatic recall on every turn
- Memory is auto-injected into the model's context from the backend
- `memory="inprocess"` for local/offline development
- Production swap to `"graphiti"` or `"mem0"` backends

## Code

```python
import asyncio
from coactra import Agent


async def handle_ticket(ticket_text: str, customer_id: str) -> str:
    agent = await Agent.create(
        model="claude-sonnet-4-5",
        name="support-agent",
        tenant="acme",
        token="dev-token",
        memory="inprocess",     # swap to "graphiti" or "mem0" in production
        instructions=(
            "You are a helpful support agent. Use past interactions to give "
            "consistent, personalised answers."
        ),
    )
    # Memory auto-recalls relevant context before the model sees the message,
    # and auto-stores the turn after the response.
    return await agent.run(f"[customer:{customer_id}] {ticket_text}")


async def main() -> None:
    # First ticket
    r1 = await handle_ticket("My dashboard is loading slowly", "cust-42")
    print("Turn 1:", r1)

    # Second ticket — the agent will recall turn 1 automatically
    r2 = await handle_ticket("Is the performance issue resolved?", "cust-42")
    print("Turn 2:", r2)


if __name__ == "__main__":
    asyncio.run(main())
```

## How Memory Works

coactra is a **pure connector**: it calls the backend's own `recall()` before the
model turn and `remember()` after. Ranking, consolidation, and storage are handled
entirely by the backend (Graphiti / mem0). coactra never ranks or stores facts itself.

| Backend | Dev/offline | Production |
|---|---|---|
| `"inprocess"` | Fast, no deps, ephemeral | — |
| `"mem0"` | Needs mem0 + LLM config | OSS self-hosted or cloud |
| `"graphiti"` | Needs Neo4j + LLM | Best for relational facts |

## Production Swap

```python
agent = await Agent.create(
    model="claude-sonnet-4-5",
    name="support-agent",
    tenant="acme",
    auth=oidc(issuer, client_id, client_secret),
    gateway="https://gateway/mcp",
    memory="graphiti",
    instructions="...",
)
```

Memory scope is isolated per tenant automatically.
