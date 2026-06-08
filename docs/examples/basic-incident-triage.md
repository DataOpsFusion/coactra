# Basic Incident Triage

The smallest Coactra application: one `Agent` that receives an incident description
and returns a triage plan. No Team, no Workflow — just the agent thinking.

## Demonstrates

- `Agent.create(model=, tools=, instructions=)`
- `agent.run(prompt)` — synchronous result
- plain local tools passed to the agent

## Code

```python
import asyncio
from coactra import Agent


def get_runbook(service: str) -> str:
    """Return the runbook URL for a service."""
    runbooks = {
        "nginx": "https://wiki.example.com/runbooks/nginx",
        "postgres": "https://wiki.example.com/runbooks/postgres",
    }
    return runbooks.get(service, "https://wiki.example.com/runbooks/generic")


async def triage_incident(incident: str) -> str:
    agent = await Agent.create(
        model="claude-sonnet-4-5",
        name="triage-1",
        auth="dev-token",          # swap for StaticToken or authlib TokenSource in production
        tools=[get_runbook],
        instructions="You are a senior SRE. Be brief and actionable.",
    )
    return await agent.run(f"Triage this incident: {incident}")


if __name__ == "__main__":
    result = asyncio.run(triage_incident("nginx is returning 502 on /api/checkout"))
    print(result)
```

## Run

```bash
python basic_incident_triage.py
```

## Production Notes

| Concern | Dev default | Production |
|---|---|---|
| Auth | `auth="dev-token"` | `StaticToken` or authlib/httpx-oauth `TokenSource` |
| MCP tools | local functions only | `gateway="https://gateway/mcp"` with `auth=` |
| Model | provider string (`anthropic:...`) | pydantic-ai `Model` instance or `gateway=` token scopes |

See [Concepts: Architecture](../concepts/architecture.md) for the full Agent/Team/Workflow model.
