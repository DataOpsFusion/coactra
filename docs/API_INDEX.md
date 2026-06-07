# API Index

Complete public surface for Coactra 0.0.x (alpha). Tags: **Available** = works today; **Advanced seam** = available but requires host wiring or optional runtime adapters.

## Top-Level Exports

```python
from coactra import Agent, RemotePeer, Run, Skill, StaticToken, Team, Workflow, mcp, oidc, serve_agent, step
```

| Name | Type | Status | Description |
|------|------|--------|-------------|
| `Agent` | class | **Available** | The single entry point for model, tools, memory, workspace, skills, peers, and learned procedure replay. |
| `RemotePeer` | dataclass | **Available** | Remote A2A peer config for outbound delegation tools. |
| `Run` | class | **Available** | Handle returned by `agent.send(...)`; supports `stream()` and `wait()`. |
| `Skill` | dataclass | **Available** | Structured skill entry for the Agent Card. |
| `StaticToken` | class | **Available** | Pre-fetched JWT token source for dev / CI. |
| `Team` | class | **Available** | Agent roster with capability routing and same-tenant policy. |
| `Workflow` | class | **Available** | Playbook runner with capability routing, approvals, checkpoint resume, and engine bridge. |
| `mcp` | function | **Available** | Declare an external MCP toolset to attach alongside local Python tools. |
| `oidc` | function | **Available** | OAuth 2.1 client-credentials token source with refresh. |
| `serve_agent` | function | **Available** | Build a Starlette A2A app for an Agent Card-backed agent. |
| `step` | function | **Available** | Build a Workflow step. |

## Public API Contract

The application-facing contract is intentionally small: start from the root `coactra` exports above. Lower-level modules such as `coactra.agent`, `coactra.workflow`, `coactra.workflow.ledger`, `coactra.team`, `coactra.team.directory`, `coactra.memory`, and `coactra.workspace` are supported seams for adapters, persistence, events, and host runtime wiring. They are not the preferred first import path for application code.

Removed alpha roots are intentionally not compatibility-shimmed; the exact banned names are enforced by the architecture guard and release checklist.

## Agent.create(...)

```python
agent = await Agent.create(
    model="anthropic/claude-sonnet-4-5",
    name="sre-1",
    tenant="acme",
    gateway="https://gateway/mcp",
    auth=oidc(token_url, client_id, client_secret),
    tools=[my_func],
    memory="graphiti",
    workspace="./desk",
    skills=[Skill(id="cert.rotate", description="...", tags=["sre"], scopes=["cert:write"])],
    peers=["security-agent"],
    expose=True,
    instructions="Be terse.",
    output=MyPydanticModel,
    tracer=tracer,
)
```

| Parameter | Type | Status | Description |
|-----------|------|--------|-------------|
| `model` | `str | model instance` | **Available** | Model id in litellm format or a pydantic-ai model instance. |
| `name` | `str` | **Available** | This agent identity. Peers reference agents by name. |
| `tenant` | `str` | **Available** | Tenant namespace. Defaults to `default`. |
| `gateway` | `str` | **Available** | Primary MCP endpoint. Token scopes slice the tool list. |
| `auth` | `TokenSource` | **Available** | Token source such as `oidc(...)` or `StaticToken`. |
| `tools` | `list` | **Available** | Local Python functions. Gateway tools are additive when `gateway=` is set. |
| `memory` | `str | backend` | **Available** | Memory backend. Auto-recall before model calls and auto-remember after. |
| `workspace` | `str` | **Available** | Path to file desk. Surfaces file and gated run tools. |
| `skills` | `list[Skill | str]` | **Available** | Curated skill roster, published as the A2A Agent Card. |
| `peers` | `list[str | Agent | RemotePeer]` | **Available** | Adds `ask_<peer>` delegation tools. Strings create unavailable placeholders; Agent objects call in-process; `RemotePeer` uses A2A transport. |
| `expose` | `bool` | **Available** | Enables an Agent Card even without explicit skills. |
| `learned` | `ProcedureVersion | list[ProcedureVersion]` | **Available** | Promoted learned procedures exposed as skills and replay tools. Raw procedures require `allow_unreviewed_learned=True`. |
| `procedure_engine` | `WorkflowEngine` | **Advanced seam** | Engine used by learned replay tools. Without it, replay tools report configuration failure. |
| `procedure_scope` | workflow `Scope` | **Advanced seam** | Override scope used by learned replay tools. |
| `allow_unreviewed_learned` | `bool` | **Available** | Explicit escape hatch for local experiments with raw procedures. Defaults to `False`. |
| `tracer` | tracer-like object | **Available** | Emits Agent run/stream spans and model request/response events. |
| `instructions` | `str` | **Available** | Optional system prompt. |
| `output` | `type` | **Available** | Pydantic model type for structured output. `run()` returns an instance. |

## run / send / stream

`agent.run(message, output=...)` returns text by default or a typed output object when `output=` is set.

`agent.send(message)` returns a `Run` handle. Call `.stream()` to iterate events or `.wait()` to await the final result.

```python
run = await agent.send("Investigate the latency spike.")
async for event in run.stream():
    ...
result = await run.wait()
```

Stream events are frozen dataclasses with `run_id` and `seq`: `Assistant`, `Thinking`, `ToolCall`, `ToolResult`, `Usage`, and terminal `Status`.

## Agent Card And A2A Serving

```python
card = agent.card
app = agent.serve(url="https://sre.example/a2a")
```

`agent.card` contains curated `name`, `tenant`, `skills`, and `securitySchemes`. Raw tool names, arguments, tokens, and credentials are never published. `agent.serve()` and `serve_agent(agent)` build the inbound A2A app; outbound delegation is configured with `peers=`.

## RemotePeer(...)

```python
from coactra import Agent, RemotePeer

agent = await Agent.create(
    model="anthropic/claude-haiku-4-5",
    name="sre-agent",
    tenant="acme",
    peers=[RemotePeer(
        name="security-agent",
        endpoint="https://security.example/a2a",
        audience="security-agent",
    )],
)
```

`RemotePeer` creates an `ask_<name>` tool backed by the official A2A transport. Same-tenant policy is enforced before the wire is touched. A plain string peer is accepted for the documented `peers=["name"]` shape, but without a registry or remote config it reports unavailable.

## Learned Procedures

```python
agent = await Agent.create(
    model="anthropic/claude-haiku-4-5",
    learned=[promoted_version],
    procedure_engine=engine,
)
```

`learned=` accepts promoted `ProcedureVersion` objects by default. This preserves the candidate -> review -> promote trust boundary. For local experiments only, raw procedures can be enabled with `allow_unreviewed_learned=True`.

## Skill(...)

```python
Skill(
    id="cert.rotate",
    description="Rotate TLS certs for any acme.example domain.",
    tags=["sre", "tls"],
    scopes=["cert:write"],
)
```

A plain string is also accepted anywhere `Skill` is: `skills=["cert rotation, vault, secrets"]`.

## oidc(...)

```python
auth = oidc(
    token_url="https://auth.example.com/realms/prod/protocol/openid-connect/token",
    client_id="sre-agent",
    client_secret="...",
)
```

OAuth client-credentials flow. Fetches the token on first use and auto-refreshes before expiry. Pass the result to `auth=` on `Agent.create`.

## Event Module

```python
from coactra.agent import (
    Agent, Run, RunResult,
    Assistant, Thinking, ToolCall, ToolResult, Usage, Status,
    Event,
)
```

Application code should prefer root imports for the main nouns (`Agent`, `Team`, `Workflow`, `Skill`, `RemotePeer`) and `coactra.agent` for lower-level event/runtime types.

## Errors

`coactra.errors` defines the error taxonomy. All coactra errors extend `CoactraError` and carry an `ErrorCode` and a `retryable` hint. Streamed failures surface as terminal `Status(state="error")` events and `RunResult.failed(...)` when a streamed run is awaited.
