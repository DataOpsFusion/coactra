# Bring Your Own Stack

Coactra is a composition shell. These pieces are intentionally **not** bundled —
use the mature library for each concern and wire it through Coactra's seams.

## Model Routing

Team-facing model selection is routed through `ModelResolver`:

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="ops"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="cheap-chat",
            profile=ModelProfile(
                name="cheap-chat",
                model="openai/qwen3.6-plus",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    model_capability="cheap-chat",
    name="sre-agent",
    instructions="Be terse.",
)
```

For deterministic or fully local development, point the route at `TestModel()` or `FunctionModel(...)` instead of a live provider.

## OAuth / MCP gateway auth

Coactra ships `StaticToken` for dev and pre-fetched bearer tokens:

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, StaticToken, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="tools"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="tool-agent",
            profile=ModelProfile(
                name="tool-agent",
                model="openai/qwen3.6-plus",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    model_capability="tool-agent",
    name="tool-agent",
    gateway="https://gateway.example/mcp",
    auth=StaticToken("your-token"),
)
```

For OAuth 2.1 client-credentials fetch and refresh, use **authlib** or **httpx-oauth** and pass any object implementing `async def token() -> str` to `auth=`.

## Inbound A2A serving

Coactra does not assemble Starlette A2A apps. Use the official **a2a-sdk** server APIs and call your agent handler directly:

```python
async def handle_message(text: str) -> str:
    return await agent.run(text)
```

## Outbound A2A delegation

Use `peers=` with local agents or `RemotePeer`:

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, RemotePeer, Scope, Team

team = Team(
    scope=Scope(tenant_id="acme", namespace="delegation"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="orchestrator",
            profile=ModelProfile(
                name="orchestrator",
                model="openai/qwen3.6-plus",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    model_capability="orchestrator",
    name="orchestrator",
    peers=[RemotePeer(
        name="security-agent",
        endpoint="https://security.example/a2a",
        audience="security-agent",
    )],
)
```

## Token exchange (RFC 8693)

For delegated identity without token passthrough, use `KeycloakExchanger` from `coactra.agent.adapters` (optional `coactra[oauth]` extra).

## What Coactra owns

| Keep in Coactra | Bring your own |
|---|---|
| `Team`, `Workflow`, `Run`, `Policy`, `Scope` | LiteLLM/OpenAI-compatible gateway deployment |
| Model routing contract (`ModelResolver`) | provider credentials and key rotation |
| Peer delegation policy and wiring | OAuth client-credentials (`authlib`) |
| Memory/workspace connectors | inbound A2A Starlette app (`a2a-sdk`) |
