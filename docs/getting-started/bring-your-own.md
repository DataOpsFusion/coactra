# Bring Your Own Stack

Coactra is a composition shell. These pieces are intentionally **not** bundled —
use the mature library for each concern and wire it through Coactra's seams.

## Model (pydantic-ai)

Pass a pydantic-ai `Model` instance for full provider control:

```python
from pydantic_ai.models.anthropic import AnthropicModel
from coactra import Agent

agent = await Agent.create(
    model=AnthropicModel("claude-haiku-4-5"),
    instructions="Be terse.",
)
```

Provider strings also work (`anthropic:claude-haiku-4-5`) — pydantic-ai resolves them
natively. Coactra does not ship a LiteLLM model adapter on the Agent path; use
`coactra[ai]` separately when you need LiteLLM routing outside the Agent facade.

## OAuth / MCP gateway auth

Coactra ships `StaticToken` for dev and pre-fetched bearer tokens:

```python
from coactra import Agent, StaticToken

agent = await Agent.create(
    model="anthropic:claude-sonnet-4-5",
    gateway="https://gateway.example/mcp",
    auth=StaticToken("your-token"),
)
```

For OAuth 2.1 client-credentials fetch and refresh, use **authlib** or
**httpx-oauth** and pass any object implementing `async def token() -> str` to
`auth=`.

## Inbound A2A serving

Coactra does not assemble Starlette A2A apps. Use the official **a2a-sdk** server
APIs and call your agent handler directly:

```python
async def handle_message(text: str) -> str:
    return await agent.run(text)
```

`agent.card` provides curated discovery metadata (`name`, `skills`, `tenant`).
Convert it to the SDK's `AgentCard` type at your server boundary if required.

## Outbound A2A delegation

Use `peers=` with local agents or `RemotePeer`:

```python
from coactra import Agent, RemotePeer

agent = await Agent.create(
    model="anthropic:claude-haiku-4-5",
    peers=[RemotePeer(
        name="security-agent",
        endpoint="https://security.example/a2a",
        audience="security-agent",
    )],
)
```

For custom transport, pass `client=` on `RemotePeer` or import
`OfficialA2ATransport` from `coactra.agent.adapters`.

## Token exchange (RFC 8693)

For delegated identity without token passthrough, use `KeycloakExchanger` from
`coactra.agent.adapters` (optional `coactra[oauth]` extra).

## What Coactra owns

| Keep in Coactra | Bring your own |
|---|---|
| `Team`, `Workflow`, `WorkManager` | pydantic-ai `Model` |
| `CollaborationPolicy`, `peer_tools` | OAuth client-credentials (`authlib`) |
| Memory/workspace connectors | Inbound A2A Starlette app (`a2a-sdk`) |
| `Scope` tenant plumbing | LiteLLM routing (`coactra[ai]` or direct) |
