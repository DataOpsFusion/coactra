# API Index

Complete public surface for Coactra 0.0.x (alpha). Tags: **Available** = works today; **Advanced seam** = available but requires host wiring or optional runtime adapters.

## Top-Level Exports

```python
from coactra import (
    Agent, RemotePeer, Run, Scope, Skill, StaticToken, Team, Workflow,
    CoactraError, ErrorCode, MissingExtraError, ValidationError,
    __version__,
)
```

| Name | Type | Status | Description |
|------|------|--------|-------------|
| `Agent` | class | **Available** | Thin facade over pydantic-ai: model, tools, memory, workspace, skills, peers, learned procedure replay. |
| `RemotePeer` | dataclass | **Available** | Remote A2A peer config for outbound delegation tools. |
| `Run` | class | **Available** | Handle returned by `agent.send(...)`; supports `stream()` and `wait()`. |
| `Scope` | dataclass | **Available** | Canonical composed-app scope DTO (`tenant_id`, `namespace`, `agent_id`, `session_id`). |
| `Skill` | dataclass | **Available** | Structured skill entry for the Agent Card. |
| `StaticToken` | class | **Available** | Pre-fetched JWT token source for dev / CI. |
| `Team` | class | **Available** | Agent roster with capability routing and same-tenant policy. |
| `Workflow` | class | **Available** | Playbook runner with capability routing, approvals, checkpoint resume, and engine bridge. |
| `CoactraError` | class | **Available** | Base exception for all Coactra errors. |
| `ErrorCode` | enum | **Available** | Machine-readable error categories (TIMEOUT, VALIDATION, PROVIDER, etc.). |
| `MissingExtraError` | class | **Available** | Raised when an optional extra is required but not installed. |
| `ValidationError` | class | **Available** | Input or contract validation failed. |
| `__version__` | str | **Available** | Installed distribution version. |

## Public API Contract

The application-facing contract is intentionally small: start from the root `coactra` exports above. Lower-level modules such as `coactra.agent`, `coactra.workflow`, `coactra.workflow.ledger`, `coactra.memory`, and `coactra.workspace` are supported seams for adapters, persistence, events, and host runtime wiring. They are not the preferred first import path for application code.

`from coactra import Team` is the stable roster API. Deep imports from `coactra.team.directory` (org stores, authorization, bootstrap helpers) are **beta** — useful for host wiring but not compatibility-promised at v1.

For OAuth client-credentials token fetch/refresh, use `authlib` or `httpx-oauth` and pass the result to `auth=` via `StaticToken` or a custom `TokenSource`. For inbound A2A serving, use the official `a2a-sdk` server APIs directly; the agent handler is `await agent.run(message)`. See [Bring Your Own Stack](getting-started/bring-your-own.md) for full recipes.

Removed alpha roots are intentionally not compatibility-shimmed; the exact banned names are enforced by the architecture guard and release checklist.

## Agent.create(...)

```python
from pydantic_ai.models.anthropic import AnthropicModel

agent = await Agent.create(
    model=AnthropicModel("claude-haiku-4-5"),
    name="sre-1",
    tenant="acme",
    gateway="https://gateway/mcp",
    auth=StaticToken("dev-token"),
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
| `model` | pydantic-ai `Model` or provider string | **Available** | Pass a pydantic-ai `Model` instance for full provider control, or a provider string such as `"anthropic:claude-haiku-4-5"`. |
| `name` | `str` | **Available** | This agent identity. Peers reference agents by name. |
| `tenant` | `str` | **Available** | Tenant namespace. Defaults to `default`. |
| `gateway` | `str` | **Available** | Primary MCP endpoint. Token scopes slice the tool list. |
| `auth` | `TokenSource` | **Available** | Token source such as `StaticToken` or a custom async `token()` provider. |
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

## Agent Card And Delegation

```python
card = agent.card
```

`agent.card` contains curated `name`, `tenant`, `skills`, and `securitySchemes`. Raw tool names, arguments, tokens, and credentials are never published. Outbound delegation is configured with `peers=`. For inbound A2A serving, wire the official `a2a-sdk` server and call `await agent.run(message)` in your handler.

## RemotePeer(...)

```python
from coactra import Agent, RemotePeer

agent = await Agent.create(
    model="anthropic:claude-haiku-4-5",
    name="sre-agent",
    tenant="acme",
    peers=[RemotePeer(
        name="security-agent",
        endpoint="https://security.example/a2a",
        audience="security-agent",
    )],
)
```

`RemotePeer` creates an `ask_<name>` tool backed by the official A2A transport (`coactra.agent.adapters.OfficialA2ATransport`). Same-tenant policy is enforced before the wire is touched. A plain string peer is accepted for the documented `peers=["name"]` shape, but without a registry or remote config it reports unavailable.

## Learned Procedures

```python
agent = await Agent.create(
    model="anthropic:claude-haiku-4-5",
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

## Scope(...)

```python
from coactra import Scope

scope = Scope(
    tenant_id="acme",
    namespace="support",
    agent_id="triage",
    session_id="session-1",
)
```

Use `to_memory_kwargs()`, `to_workspace_kwargs()`, and related helpers at package boundaries. Per-module `Scope` types in `coactra.memory`, `coactra.workspace`, and `coactra.workflow` are different classes — qualify imports when crossing packages.

## MCPServer(...) and workflow steps

Additive external MCP servers (not the primary `gateway=` path):

```python
from coactra.agent import MCPServer

agent = await Agent.create(
    model="anthropic:claude-haiku-4-5",
    tools=[MCPServer(url="https://tools.example/mcp", name="extra")],
)
```

Workflow playbook steps:

```python
from coactra.workflow import step, PlaybookStep

wf = Workflow("release", steps=[
    step("Run checks", needs="test"),
    PlaybookStep(instruction="Approve", approve=True),
])
```

`coactra.workflow.Step` is a separate graph-node type for durable procedure engines.

## Outbound A2A Adapters

```python
from coactra.agent.adapters import OfficialA2ATransport, OfficialA2AClient
```

Minimal outbound transport over the official `a2a-sdk`. For inbound serving, use `a2a-sdk` server APIs directly.

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
