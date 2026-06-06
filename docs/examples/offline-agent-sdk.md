# Offline Agent SDK

Create an `Agent` with local tools and stream its events — no network model required
for offline development. Swap in a real model id when you're ready.

## Demonstrates

- `Agent.create(model=, tools=, instructions=)`
- `agent.send(prompt).stream()` — async event stream
- `Assistant`, `ToolCall`, `ToolResult`, `Usage`, `Status` events
- offline model substitution (use any litellm-compatible id)

## Code

```python
import asyncio
from coactra import Agent


def check_disk(host: str) -> dict:
    """Return disk usage for a host (stub for offline demo)."""
    return {"host": host, "used_pct": 78, "free_gb": 22}


def restart_service(host: str, service: str) -> str:
    """Restart a service on a host."""
    return f"Restarted {service} on {host}"


async def main() -> None:
    agent = await Agent.create(
        model="claude-haiku-4-5",   # fast/cheap; swap to your offline model id
        name="sre-agent",
        token="dev-token",
        tools=[check_disk, restart_service],
        instructions="You are an SRE agent. Check before you act.",
    )

    print("Streaming response:")
    async for event in agent.send("Check disk on web-01 and restart nginx if >80%").stream():
        print(event)


if __name__ == "__main__":
    asyncio.run(main())
```

## Event Types

| Event | Description |
|---|---|
| `Assistant` | Text chunk from the model |
| `Thinking` | Internal reasoning (thinking models) |
| `ToolCall` | Tool the agent is invoking |
| `ToolResult` | Result returned to the agent |
| `Usage` | Token counts at end |
| `Status` | Run lifecycle (`started`, `done`, `error`) |

## Production Notes

| Concern | Dev default | Production |
|---|---|---|
| Auth | `token="dev-token"` | `auth=oidc(issuer, client_id, client_secret)` |
| Tools via gateway | — | `gateway="https://gateway/mcp"` + `auth=` |
| Model | local id | any litellm-compatible provider id |
