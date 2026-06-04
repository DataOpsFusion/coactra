# Design: Turnkey, elegant Agent SDK (A2A + MCP + capabilities)

- Date: 2026-06-04
- Status: Draft for review
- Scope: `coactra-agent` (new SDK surface) + a small async extension to `coactra-ai`; re-export from the `coactra` umbrella. No changes to existing `make_agent` / `coactra.agent.Agent` behavior.

## 1. Summary

Add a new, elegant, async, Cursor-SDK-style facade — `from coactra import Agent` — that lets a user create an agent in one declarative call and get, out of the box: model access (via litellm), MCP tools (client), the ability to call other agents (A2A outbound), the ability to be reached by other agents (A2A inbound server), exposure of itself as an MCP server, plus the rest of coactra's capabilities (memory, workspace, organization, durable work) wired in and usable both as ergonomic methods and as tools the agent can use autonomously.

The north star is the Cursor TypeScript SDK (`Agent.create` / `agent.send` / `run.stream` / `run.wait`, declarative `mcpServers`, sticky per-run overrides, async disposal). The goal is to save library users a large amount of wiring, leaning on the fact that coactra already proxies everything through litellm/instructor (so structured/JSON output is essentially free).

This facade is a thin composition layer **on top of** the existing low-level ports and `make_agent`; it does not replace them.

## 2. Motivation and current gaps

`make_agent` already exposes the seams (`mcp=`, `transport=`, six capability ports), but the turnkey experience is missing:

- **MCP is metadata-only.** Mounting exposes tool names/specs (`tools_specs()`); the agent never *invokes* a tool. There is no MCP client and no `call_tool`. `FastMCPServer` (expose-as-MCP) is a stub that raises.
- **A2A inbound is not bundled.** `build_a2a_app` exists but the host must hand-build an agent card, verifier, and handler.
- **Config is "bring a constructed port object,"** not Cursor's declarative `{type, url}`.
- **The AI seam is sync and text-only.** `coactra.ai.Client` exposes `ask()` / `structured()` over `litellm.completion`; there is no async, tool-calling, or streaming path — all of which an agentic loop needs.
- **`Agent.think()` is sync,** but A2A/MCP are network I/O; the elegant surface should be async-first.

## 3. Goals / Non-goals

Goals:
- One declarative `Agent.create(...)` that wires model + MCP + A2A (in/out) + memory + workspace + organization + work.
- Async-first surface: `send → run.stream()/run.wait()`, `ask(Schema)`, `call(peer, msg)`, `serve()`.
- Configured capabilities auto-exposed as tools the loop can use, plus auto-memory (recall before / remember after) — all toggleable ("full auto" default).
- Strict backward compatibility: `make_agent` and `coactra.agent.Agent` unchanged.
- Offline-first defaults and tests.

Non-goals (deferred, noted as future seams):
- `Agent.resume(agent_id)` durable session replay (needs a persistence store).
- A synchronous wrapper (`Agent.create_sync`).
- Replacing the built-in loop with a durable runtime (LangGraph/Temporal/pydantic-ai) — this is the planned "Approach 2" upgrade, kept possible by hiding the loop behind a port.
- Full enforcement of approval tiers inside the loop (a hook point is added; enforcement is a follow-up).

## 4. Public API

`from coactra import Agent` (new facade; distinct from internal `coactra.agent.Agent`, which it wraps).

### 4.1 Create

```python
agent = await Agent.create(
    model="anthropic/claude-sonnet-4-6",          # litellm id (required)
    instructions="You are an SRE triage assistant.",
    # tools & agents
    mcp={                                          # MCP tool servers (client)
        "docs": {"type": "http", "url": "https://…/mcp", "auth": {...}},
        "fs":   {"type": "stdio", "command": "npx", "args": [...]},
    },
    peers={"dba": {"url": "https://dba.internal"}},  # A2A outbound targets
    serve=True,                                     # stand up THIS agent's A2A inbound
    expose_mcp=False,                              # also publish agent AS an MCP server
    # the rest of the capabilities — same declarative shape
    memory="graphiti",                            # or {"backend": "graphiti", "neo4j": {...}}
    workspace="local",                            # or {"backend": "daytona", ...} (stubs raise clearly)
    organization={"backend": "sqlite", "url": …}, # roles/hierarchy → A2A policy + escalation
    work={"store": "sql", "url": …},              # durable work orders
    # identity / multi-tenancy / provider
    scope=Scope("acme", "agent:sre"),             # optional → defaults to Scope("local","agent")
    api_key=..., api_base=...,                     # litellm provider config
    # behavior toggles (defaults shown = "full auto")
    auto_memory=True,
    capabilities_as_tools=True,
    max_steps=12,                                 # loop safety bound
    # escape hatches (advanced): ai=, memory_port=, workspace_port=, tools=[py fns],
    #   policy=, verifier=, exchanger=, transport=, conflict_policy=
)
```

Each capability accepts **string shorthand** or a **dict**; each defaults to the existing in-process/local fake so the zero-config path still works. Stub backends (Daytona/E2B/OpenHands/Neo4j-org) raise a clear `MissingExtraError`.

### 4.2 Run / stream / structured

```python
run = await agent.send("triage the db latency incident")     # → Run handle
async for ev in run.stream():                                 # typed events
    match ev:
        case Assistant(text): ...
        case Thinking(text): ...
        case ToolCall(name, args): ...
        case ToolResult(name, result): ...        # result carries .error on failure
        case AgentCall(peer, question): ...        # A2A hop
        case AgentResult(peer, answer): ...
        case Status(state): ...                    # running | finished | error | cancelled
result = await run.wait()        # RunResult(text, structured, tool_calls, usage, messages, status)

plan: TriagePlan = await agent.ask(TriagePlan, "give a 3-step plan")   # typed (instructor)
answer = await agent.run("…")    # convenience = send + wait, no streaming
reply  = await agent.call("dba", "is replication lagging?")            # A2A outbound by name
```

Per-`send` overrides (`model=`, `mcp=`, `auto_memory=`) mirror Cursor's sticky per-run overrides.

### 4.3 Capability methods (ergonomic surface)

```python
await agent.remember("primary db failover at 02:14");  facts = await agent.recall("db incidents", k=5)
await agent.fs.write("notes/triage.md", "…");          text  = await agent.fs.read("notes/triage.md")
out   = await agent.fs.run("psql -c 'select 1'")        # policy-gated exec
order = await agent.submit("Triage db latency");        st    = await agent.work.get(order.id)
if await agent.can("restart_db"): ...;                  boss  = await agent.manager
await agent.escalate(order, reason="needs DBA sign-off")
agent.tools                                             # mounted tool names
await agent.mount("name", {...})                        # mid-session MCP mount
```

### 4.4 Serving / lifecycle / sugar

```python
app = agent.app                       # turnkey A2A inbound ASGI app (serve=True)
await agent.serve(host="0.0.0.0", port=8016)
mcp_app = agent.mcp_app               # agent published AS MCP server (expose_mcp=True)

async with Agent.create(...) as agent:    # auto-close (Cursor's `await using`)
    ...
await agent.aclose()
await Agent.prompt("…", model="…")    # one-shot, no handle
```

### 4.5 Events and results (DTOs)

Small, frozen, discriminated dataclasses in `coactra.agent.sdk`:
`Assistant(text)`, `Thinking(text)`, `ToolCall(id, name, args)`, `ToolResult(id, name, result, error)`, `AgentCall(peer, question)`, `AgentResult(peer, answer)`, `Status(state)`.
`RunResult(status, text, structured, tool_calls, usage, messages, error)`.

## 5. Behavior: "full auto" (default, all toggleable)

- **capabilities_as_tools=True**: configured capabilities are registered as tools the model may call inside `send()` — `recall`, `remember`, `fs_read`, `fs_write`, `fs_run`, `work_submit`, `call_agent` — alongside MCP tools. Each is registered only when its capability is configured.
- **auto_memory=True** (when `memory` configured): before a `send`, recall top-k relevant facts and inject them into the system context; after the run, distill salient facts and remember them (reusing `coactra.workspace.integrations.memory`'s distiller). Disable via `auto_memory=False` or per-send.

## 6. Architecture

New subpackage (nothing existing changes):

```
coactra/agent/sdk/
  facade.py      # Agent, Run, RunResult, event dataclasses   ← re-exported as coactra.Agent
  loop.py        # the async agentic tool-use loop (Approach 1)
  config.py      # declarative dict/shorthand → real backends (reuses make_coactra_agent)
  tools.py       # capability→tool bridge (MCP tools + memory/fs/work/peer as one registry)
  mcp_client.py  # NEW real MCP client (http + stdio) implementing MCPClientPort
  serve.py       # turnkey A2A inbound app (card + verifier) + expose-as-MCP server
adapters/fastmcp.py    # un-stub → real FastMCP server (expose agent AS MCP)
```

Cross-package change (one boundary-respecting unit, sequenced first):

- **`coactra-ai`**: add an async, tool-calling, streaming completion path on the `Completer` seam, e.g. `async def acomplete(model, messages, *, tools=None, stream=False)` returning a normalized result that carries either text deltas or tool-call requests. Uses `litellm.acompletion(..., tools=, stream=True)`. Preserves the existing `reasoning_content` fallback. No new dependency. `ask()`/`structured()` stay as-is.

### 6.1 The loop (`loop.py`, Approach 1)

1. Build messages: system (instructions + auto-recalled memory) + prior turns + user input.
2. Call the async completer with the unified tool specs (`stream=True`); emit `Assistant`/`Thinking` deltas.
3. If the model returns tool calls: dispatch each through the tool registry, emit `ToolCall` then `ToolResult` (or `AgentCall`/`AgentResult` for `call_agent`); append results to messages; loop.
4. Stop when the model returns no tool calls (final) or `max_steps` is hit (emit `Status("error")` with a bounded-loop error).
5. `ask(Schema)` takes the final answer through instructor for typed output.
6. Destructive tools consult coactra's approval-tier resolver at a hook point (enforcement is a follow-up; for now the hook can log/deny by policy).

### 6.2 Capability→tool bridge (`tools.py`)

A `Tool = {name, description, json_schema, async handler}`. Sources:
- **MCP**: the new `MCPClientPort` (`list_tools()` + `call_tool(name, args)`) — `call_tool` is the missing piece. Tool specs feed the registry; handlers call the client.
- **Capabilities**: built-in tools wrapping `memory.recall/remember`, `workspace.read/write/run`, `work.submit`, `collaborator.call` — registered only when configured and `capabilities_as_tools=True`.
- Name conflicts reuse the existing `MountRegistry`/`ToolTrie` namespacing and `ConflictPolicy`.

### 6.3 MCP client + server

- `mcp_client.py`: real client over the MCP SDK / FastMCP client supporting `{"type":"http","url",...}` and `{"type":"stdio","command","args"}`. Implements `MCPClientPort`. Lifecycle (connect/list/close) tied to the Agent's `aclose()`. Requires `coactra-agent[mcp]`.
- `adapters/fastmcp.py`: un-stub into a real FastMCP server that publishes the agent as MCP tools (`ask`, `run`), gated by `expose_mcp=True`/`agent.mcp_app`.

### 6.4 A2A bundle (`serve.py`)

- Inbound (`serve=True`): build the a2a-sdk agent card from scope/role/instructions + tool list; default JWT verifier (local mode → no-auth with a loud warning; production → requires verifier per existing inbound contract); `build_a2a_app(card, handler=→agent.run, verifier)`. Surfaced as `agent.app` / `await agent.serve()`.
- Outbound (`peers={...}`): build `OfficialA2ATransport` with endpoint/audience resolvers derived from the peers dict, behind the existing `PolicyGatedCollaborator` (+ `organization` policy when configured). Drives `agent.call(peer, …)` and the `call_agent` tool. Token exchange via the configured `exchanger` (InProcess by default; Keycloak when configured).

## 7. Configuration reference

| Capability | Shorthand | Dict form | Backends |
|---|---|---|---|
| `model` | `"anthropic/claude-sonnet-4-6"` | — | any litellm id |
| `mcp` | — | `{name: {type:"http"\|"stdio", ...}}` | new MCP client |
| `peers` | — | `{name: {url, audience?}}` | OfficialA2ATransport |
| `memory` | `"inprocess"\|"mem0"\|"graphiti"` | `{backend, ...}` | `coactra.memory.make_backend` |
| `workspace` | `"local"` | `{backend, root?, ...}` | local (impl); daytona/e2b/openhands (stub) |
| `organization` | `"sqlite"` | `{backend:"sqlite"\|"postgres", url}` | Sqlite/AsyncPostgres OrgStore |
| `work` | — | `{store:"memory"\|"sql", url?}` | InMemory/Sql WorkStore |

## 8. Errors

Typed `coactra.errors.CoactraError` with `ErrorCode`. Tool failures surface as `ToolResult(error=…)` and (by policy) either continue or abort the loop; A2A denials raise `CollaborationDenied`; provider/timeout/validation map to existing codes. `RunResult.status` ∈ {finished, error, cancelled}; streaming ends with a terminal `Status`.

## 9. Scope and multi-tenancy

`scope` is optional, defaulting to `Scope("local","agent")`. It is threaded into every backend exactly as today (memory scope key, tenant-namespaced workspace root, A2A tenant qualification, work scope). Cross-tenant denial is preserved via `AllowSameTenant` / the configured `organization` policy. `me` (self identity) derives from `scope.namespace` unless overridden.

## 10. Backward compatibility & packaging

- `make_agent` and `coactra.agent.Agent` are untouched; the facade composes them.
- New `coactra-agent[mcp]` extra pulls the MCP client/server deps. A2A deps follow the existing agent extras.
- Additive minor version bumps (`coactra-ai`, `coactra-agent`, umbrella re-export) with changelog entries per `docs/RELEASE_POLICY.md`.
- Public API additions registered in `docs/API_INDEX.md` / `public_api.json` (the CI `check_public_api.py` guard).

## 11. Testing strategy (offline-first)

- A fake in-process MCP client (a small tool server) + a scripted fake completer that emits tool-calls then a final answer drive the loop deterministically with no network.
- `MCPClientPort` conformance suite (mirrors existing port conformance tests).
- A2A inbound/outbound round-trip against the existing fakes (`NullTransport`, in-memory task store).
- `examples/elegant_agent.py` runs fully on fakes (examples-as-tests).
- CI: add a `coactra-agent[mcp]` lane.

## 12. Work units (sequenced, boundary-respecting)

1. **`coactra-ai`**: async tool-calling + streaming completion path on the `Completer` seam (+ tests).
2. **`coactra-agent` / `mcp_client.py` + `MCPClientPort`**: real MCP client (http+stdio), `call_tool`, conformance + fake (+ extra).
3. **`coactra-agent` / `tools.py`**: capability→tool bridge over the existing mount registry.
4. **`coactra-agent` / `loop.py`**: the async agentic loop + events.
5. **`coactra-agent` / `serve.py` + `adapters/fastmcp.py`**: A2A inbound bundle + expose-as-MCP server.
6. **`coactra-agent` / `facade.py` + `config.py`**: `Agent.create/send/run/ask/call/serve` + declarative config (reusing `make_coactra_agent`); umbrella re-export.
7. **Docs/examples/CI**: `examples/elegant_agent.py`, API index, changelog, mcp CI lane.

## 13. Open questions / future

- `Agent.resume(agent_id)` + a session/transcript store (persistence backend choice).
- Sync wrapper (`Agent.create_sync`) over the async core.
- Approach 2: swap the in-loop runtime for LangGraph/Temporal/pydantic-ai behind the same facade (durability, checkpointing) for users who opt in.
- Enforcing approval tiers (green/yellow/red) inside the tool dispatch.
- Streaming token deltas vs message-level events granularity (start message-level; add token deltas if needed).
