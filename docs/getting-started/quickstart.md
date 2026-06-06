# Quickstart

This guide walks through the available `Agent` surface step by step. Every snippet is
copy-pasteable and matches the 0.0.x alpha API.

!!! warning "Alpha"
    The public surface is settling. `Team` and `Workflow` are designed but not yet
    shipped. Pin your version.

## 1. Install

Base install (no optional capabilities):

```bash
pip install coactra
```

Add the agent runtime (required for `Agent.create`):

```bash
pip install "coactra[agent]"
```

Add gateway + OAuth support:

```bash
pip install "coactra[agent-gateway]"
```

Add memory (Graphiti backend):

```bash
pip install "coactra[agent,graphiti]"
```

Add all:

```bash
pip install "coactra[all]"
```

For source development:

```bash
python -m pip install -e "./coactra[all,dev]"
```

## 2. Hello agent

`Agent.create` is the single entry point. Give it a model id and call `run`:

```python
import asyncio
from coactra import Agent

async def main():
    agent = await Agent.create(model="openai/gpt-4o-mini")
    answer = await agent.run("What is the first check for database latency?")
    print(answer)

asyncio.run(main())
```

Model ids use the litellm convention (`provider/model`). Any litellm-supported
provider works: `anthropic/claude-sonnet-4-5`, `openai/gpt-4o`, `groq/llama-3.1-70b-versatile`, etc.

## 3. Streaming

Use `send(...).stream()` to iterate events as they arrive. Each event is a typed
dataclass: `Assistant`, `Thinking`, `ToolCall`, `ToolResult`, `Usage`, or `Status`.

```python
import asyncio
from coactra import Agent

async def main():
    agent = await Agent.create(model="anthropic/claude-sonnet-4-5")

    async for event in agent.send("Investigate the database latency incident").stream():
        match type(event).__name__:
            case "Assistant":
                print(event.text, end="", flush=True)
            case "Thinking":
                print(f"[thinking] {event.text[:60]}…")
            case "ToolCall":
                print(f"\n→ tool: {event.name}({event.args})")
            case "ToolResult":
                print(f"← result: {event.result}")
            case "Status":
                print(f"\n[{event.state}]")

asyncio.run(main())
```

## 4. Structured output

Pass a Pydantic model to `output=` and `run()` returns a typed instance:

```python
import asyncio
from pydantic import BaseModel
from coactra import Agent

class IncidentReport(BaseModel):
    severity: str
    first_check: str
    likely_cause: str

async def main():
    agent = await Agent.create(model="openai/gpt-4o")
    report = await agent.run(
        "Triage: database p99 latency spiked to 4 s at 14:32 UTC.",
        output=IncidentReport,
    )
    print(report.severity, report.first_check)

asyncio.run(main())
```

## 5. Tools

Pass plain Python functions as tools. The model decides when to call them:

```python
import asyncio
from coactra import Agent

def get_service_status(service: str) -> str:
    """Return the current status of a named service."""
    # real implementation calls your monitoring API
    return f"{service}: healthy"

def restart_service(service: str) -> str:
    """Restart a named service and confirm."""
    return f"{service}: restarted"

async def main():
    agent = await Agent.create(
        model="anthropic/claude-sonnet-4-5",
        tools=[get_service_status, restart_service],
        instructions="You are an SRE. Be concise.",
    )
    answer = await agent.run("Restart nginx and confirm it is healthy.")
    print(answer)

asyncio.run(main())
```

## 6. Gateway + auth (token-sliced MCP tools)

The primary MCP path is `gateway=` + `auth=`. The token's OAuth scopes slice the
tool list — no manual MCP enumeration needed.

```python
import asyncio
from coactra import Agent, oidc

async def main():
    agent = await Agent.create(
        model="anthropic/claude-sonnet-4-5",
        name="sre-1",
        tenant="acme",
        gateway="https://your-mcp-gateway/mcp",
        auth=oidc(
            issuer="https://auth.acme.example/realms/prod",
            client_id="sre-agent",
            client_secret="...",          # or read from env
        ),
        instructions="You are an SRE. Only take safe, reversible actions.",
    )
    answer = await agent.run("Rotate the prod TLS cert for api.acme.example.")
    print(answer)

asyncio.run(main())
```

`oidc(...)` does OAuth 2.1 client-credentials with automatic token fetch and
refresh. The gateway uses the token's scopes to decide which tools are visible —
coactra never hard-codes a tool list.

For development / CI you can pass a pre-fetched JWT instead:

```python
agent = await Agent.create(
    model="...",
    gateway="https://your-mcp-gateway/mcp",
    token="eyJhbG...",          # short-lived JWT; expires quickly
)
```

You can also add a local/extra MCP server alongside the gateway using `mcp()`:

```python
from coactra import Agent, mcp, oidc

agent = await Agent.create(
    model="...",
    gateway="https://your-mcp-gateway/mcp",
    auth=oidc(...),
    tools=[mcp("http://localhost:8001/mcp")],   # additive — not the primary path
)
```

## 7. Memory

Pass a backend name to `memory=` and the agent auto-recalls context on every turn
and auto-remembers after each turn. coactra is the connector — the backend
(graphiti / mem0) owns ranking and consolidation.

```python
import asyncio
from coactra import Agent, oidc

async def main():
    agent = await Agent.create(
        model="anthropic/claude-sonnet-4-5",
        name="support-1",
        tenant="acme",
        memory="graphiti",          # backend name; requires coactra[graphiti]
    )
    await agent.run("The prod DB hit OOM last Tuesday; root cause was a missing index.")
    # Next turn: the agent auto-recalls the above fact.
    answer = await agent.run("What do you remember about the prod DB?")
    print(answer)

asyncio.run(main())
```

## 8. Workspace

Pass a directory path to `workspace=` and the agent gains read/write/list/run
tools over that desk. `run` is allow-list gated by default.

```python
import asyncio
from coactra import Agent

async def main():
    agent = await Agent.create(
        model="anthropic/claude-sonnet-4-5",
        workspace="./desk",         # agent desk directory
        instructions="Summarize all .log files in the desk.",
    )
    answer = await agent.run("Analyze the logs.")
    print(answer)

asyncio.run(main())
```

## 9. Skills (Agent Card)

`skills=` is the curated roster published as an A2A Agent Card. Use a string for
simple labeling or a structured `Skill` for full A2A card metadata.

```python
import asyncio
from coactra import Agent, Skill, oidc

async def main():
    agent = await Agent.create(
        model="anthropic/claude-sonnet-4-5",
        name="sre-1",
        tenant="acme",
        gateway="https://your-mcp-gateway/mcp",
        auth=oidc(issuer="...", client_id="...", client_secret="..."),
        skills=[
            Skill(
                id="cert.rotate",
                description="Rotate TLS certificates for any acme.example domain.",
                tags=["sre", "tls"],
                scopes=["cert:write"],
            ),
            Skill(
                id="service.restart",
                description="Restart named services and confirm health.",
                tags=["sre", "ops"],
                scopes=["service:restart"],
            ),
        ],
    )
    # The agent's card is accessible for inspection:
    print(agent.card)

asyncio.run(main())
```

Raw tool names and argument schemas are never published — only the curated
`skills=` blurb. "Seeing ≠ calling": discovery exposes only the blurb; every
A2A delegation is still auth-gated.

## 10. What's coming (designed, not yet shipped)

The following are designed and on the build roadmap but not available in 0.0.x:

- **`Team`** — group agents for capability-routing, shared policy, and hierarchy.
- **`Workflow`** — a playbook runner with step assignment, durable execution, retries, and approvals.
- **`peers=`** — outbound A2A delegation targets on `Agent.create`.
- Full A2A serving (the `expose=True` default).

See [Architecture](../concepts/architecture.md) for the full model and build order.
