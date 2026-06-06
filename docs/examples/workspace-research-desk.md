# Workspace Research Desk

An agent with a **workspace** — a persistent desk where it can read and write files
between tasks and sessions. The agent gets `read_file`, `write_file`, `list_files`,
and (if configured) `run` as automatic tools from the workspace path.

## Demonstrates

- `Agent.create(workspace="./desk")` — capability by path
- Workspace surfaces as tools the model can call directly
- `run` is allow-listed (disabled by default; must be explicitly enabled)
- Persistent notes across sessions (files live in the workspace path)

## Code

```python
import asyncio
from coactra import Agent


async def research_session(topic: str) -> str:
    agent = await Agent.create(
        model="claude-sonnet-4-5",
        name="research-agent",
        tenant="acme",
        token="dev-token",
        workspace="./desk",         # creates ./desk if not present
        instructions=(
            "You are a research assistant. Use the workspace to take notes, "
            "store findings, and write a summary file when done."
        ),
    )
    return await agent.run(f"Research {topic} and save a summary to summary.md")


if __name__ == "__main__":
    result = asyncio.run(research_session("TLS certificate rotation best practices"))
    print(result)
```

## Workspace Tools

When `workspace=` is set, the agent automatically receives these tools:

| Tool | Description |
|---|---|
| `read_file(path)` | Read a file from the workspace |
| `write_file(path, content)` | Write content to a file |
| `list_files(path?)` | List files in the workspace |
| `run(cmd)` | Execute a command — **disabled by default**, require explicit allow-list |

## Security Notes

- `run` is gated by an allow-list. Never enable broad shell access for untrusted tenants.
- Workspace path is scoped per-tenant; cross-tenant file access is denied.
- For untrusted workloads, use a sandbox-backed workspace adapter (Daytona, E2B, OpenHands) rather than local filesystem.

## Production Notes

| Concern | Dev default | Production |
|---|---|---|
| Auth | `token="dev-token"` | `auth=oidc(issuer, client_id, client_secret)` |
| Workspace backend | Local filesystem | Sandbox/remote backend |
| `run` commands | Disabled | Explicit allow-list per tenant |
