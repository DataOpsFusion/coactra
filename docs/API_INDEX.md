# API Index

Complete public surface for Coactra 0.0.x (alpha). Tags: **Available** = works today; **Designed / coming** = fully specified, not yet shipped.

## Top-level exports

```python
from coactra import Agent, Skill, oidc, StaticToken, mcp
```

| Name | Type | Status | Description |
|------|------|--------|-------------|
| `Agent` | class | **Available** | The single entry point. See below. |
| `Skill` | dataclass | **Available** | Structured skill entry for the Agent Card. |
| `oidc` | function | **Available** | OAuth 2.1 client-credentials token source (fetch + refresh). |
| `StaticToken` | class | **Available** | Pre-fetched JWT token source for dev / CI. |
| `mcp` | function | **Available** | Tag an extra MCP server URL for `tools=`. |
| `Team` | class | **Designed / coming** | Agent roster with capability routing and policy. |
| `Workflow` | class | **Designed / coming** | Playbook runner with durable step execution. |
| `step` | function | **Designed / coming** | Build a Workflow step. |

## Agent.create(...)

```python
agent = await Agent.create(
    model="anthropic/claude-sonnet-4-5",  # required
    name="sre-1",
    tenant="acme",
    gateway="https://gateway/mcp",
    auth=oidc(issuer, client_id, client_secret),
    tools=[my_func, mcp("http://extra/mcp")],
    memory="graphiti",
    workspace="./desk",
    skills=[Skill(id="cert.rotate", description="...", tags=["sre"], scopes=["cert:write"])],
    instructions="Be terse.",
    output=MyPydanticModel,
    # coming:
    peers=["security-agent"],
    expose=True,
)
```

### Parameters

| Parameter | Type | Status | Description |
|-----------|------|--------|-------------|
| `model` | `str` | **Available** | Model id in litellm format (`provider/model` or bare id). |
| `name` | `str` | **Available** | This agent's identity. Peers reference agents by name. |
| `tenant` | `str` | **Available** | Tenant namespace. Defaults to `"default"`. |
| `gateway` | `str` | **Available** | Primary MCP endpoint. Token scopes slice the tool list. No manual enumeration. |
| `auth` | `oidc(...)` | **Available** | Token source: OAuth 2.1 client-credentials fetch + refresh. |
| `token` | `str` | **Available** | Pre-fetched JWT for development (`token="eyJh..."` instead of `auth=`). |
| `tools` | `list` | **Available** | Local Python functions and/or `mcp(url)` tags. Additive to the gateway. |
| `memory` | `str` | **Available** | Memory backend name (`"graphiti"`). Auto-recall + auto-remember per turn. |
| `workspace` | `str` | **Available** | Path to file desk. Surfaces `read_file`, `write_file`, `list_files`, `run` as tools. |
| `skills` | `list[Skill \| str]` | **Available** | Curated skill roster, published as the A2A Agent Card. |
| `instructions` | `str` | **Available** | Optional system prompt. |
| `output` | `type` | **Available** | Pydantic model type for structured output. `run()` returns an instance. |
| `peers` | `list[str]` | **Designed / coming** | Outbound A2A delegation targets (agent names). Separate from `tools`. |
| `expose` | `bool` | **Designed / coming** | Publish the Agent Card for inbound A2A. Defaults to `True`. |

## run / send / stream

### agent.run(message, ...)

```python
# Text answer
answer: str = await agent.run("Restart nginx and confirm.")

# Typed output
report: MyModel = await agent.run("Triage the incident.", output=MyPydanticModel)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | The prompt. |
| `output` | `type \| None` | Pydantic model for structured output. Returns model instance if set. |
| `message_history` | `list` | Prior turn messages (pydantic-ai format). |

Returns `str` when `output` is not set; returns a Pydantic model instance when `output` is set.

### agent.send(message, ...) → Run

Returns a `Run` handle. Call `.stream()` to iterate events or `.wait()` to await the final result.

```python
run = await agent.send("Investigate the latency spike.")

# Iterate events:
async for event in run.stream():
    ...

# Or await final result:
result = await run.wait()
```

### Event types (from stream)

All events are frozen dataclasses with `run_id: str` and `seq: int`.

| Event | Fields | Description |
|-------|--------|-------------|
| `Assistant` | `text: str` | A chunk of the model's text response. |
| `Thinking` | `text: str` | A chunk of the model's reasoning / thinking output. |
| `ToolCall` | `id, name, args` | The model requested a tool call. |
| `ToolResult` | `id, name, result, error` | The tool returned a result (or error). |
| `Usage` | `tokens: int, cost: float` | Token/cost accounting for the run. |
| `Status` | `state: Literal["running","finished","error","cancelled"]` | Terminal event. |

## agent.card

```python
card = agent.card    # the agent's curated A2A Agent Card
```

Returns the Agent Card object containing `name`, `skills`, and `securitySchemes`. Raw tool
names and argument schemas are never included. **Designed / coming**: full A2A publish and
peer fetch.

## Skill(...)

```python
from coactra import Skill

Skill(
    id="cert.rotate",
    description="Rotate TLS certs for any acme.example domain.",
    tags=["sre", "tls"],
    scopes=["cert:write"],
)
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Dot-namespaced skill identifier (`"cert.rotate"`). |
| `description` | `str` | Human-readable blurb published in the Agent Card. |
| `tags` | `list[str]` | Labels for Team capability matching. |
| `scopes` | `list[str]` | OAuth scopes needed to call this skill. |

A plain string is also accepted anywhere `Skill` is: `skills=["cert rotation, vault, secrets"]`.

## oidc(...)

```python
from coactra import oidc

auth = oidc(
    issuer="https://auth.example.com/realms/prod",
    client_id="sre-agent",
    client_secret="...",
)
```

OAuth 2.1 client-credentials flow. Fetches the token on first use and auto-refreshes before
expiry. Pass the result to `auth=` on `Agent.create`.

## mcp(url)

```python
from coactra import mcp

tools=[mcp("http://localhost:8001/mcp")]
```

Tag an extra MCP server URL. The server is connected and its tools are expanded into the
agent's tool list. Use for local or extra servers; the primary MCP path is `gateway=` + `auth=`.

## Event module

```python
from coactra.agent.sdk import (
    Agent, Run, RunResult,
    Assistant, Thinking, ToolCall, ToolResult, Usage, Status,
    Event,
)
```

These are re-exported at the top level; import from `coactra` directly in application code.

## Errors

`coactra.errors` defines the error taxonomy. All coactra errors extend `CoactraError` and
carry an `ErrorCode` and a `retryable` hint:

| Code | Class | Retryable |
|------|-------|-----------|
| `CONFIG` | `ConfigurationError` | No |
| `VALIDATION` | `ValidationError` | No |
| `PROVIDER` / `ADAPTER` | `AdapterError` | Per type |
| `EXECUTION` / `RUNTIME` | `ExecutionError` | Yes (bounded) |
| `TIMEOUT` | `TimeoutError` | Yes |
| `PERMISSION` | `PermissionDeniedError` | No |
| `SECURITY` | `SecurityError` | No — fail-closed + audited |
| `MISSING_EXTRA` | `MissingExtraError` | No — install the extra |

Errors surface as a terminal `Status(state="error")` event in the stream and as
`RunResult.failed(error=...)` from `run()`.
