# Design: Turnkey, elegant Agent SDK (A2A + MCP + capabilities)

- Date: 2026-06-04
- Status: Draft for review (revised after Codex review)
- Scope: `coactra-agent` (new SDK surface) backed by **pydantic-ai** as the agent runtime; a small `coactra-ai`↔pydantic-ai model bridge; re-export from the `coactra` umbrella. No changes to existing `make_agent` / `coactra.agent.Agent` behavior.

## 0. Review history

- v1 draft proposed a hand-rolled tool-use loop ("Approach 1"). Codex review (2026-06-04) argued — correctly — that this re-implements a harness, against coactra's "wrap best-of-breed, never re-implement" charter.
- **Adopted:** runtime is now **pydantic-ai** behind an `AgentRuntimePort` (provider-neutral, gives streaming/structured/usage-limits/timeouts/message-history); lifecycle bug fixed; serving split from construction; `agent.workspace` (not `fs`); structured via `run(output_type=...)`; events carry identity; timeouts/cancellation/approval/observability are v1, not deferred; sequencing revised; expose-as-MCP and org/work tools sequenced after the proven core.
- **Retained by product decision (with documented risk):** "full auto" defaults (capabilities-as-tools + auto-memory on). Safety floor that full-auto does **not** disable: A2A inbound requires a verifier; destructive tools route through the approval-tier hook.

## 1. Summary

Add an elegant, async, Cursor-SDK-style facade — `from coactra import Agent` — that creates an agent in one declarative call and gets, out of the box: model access (litellm), MCP tools (client), calling other agents (A2A out), being reached by other agents (A2A in), exposing itself as an MCP server, plus memory/workspace/organization/work wired in and usable as ergonomic methods **and** as tools the agent uses autonomously.

The facade is a thin composition layer over the existing ports/`make_agent`. The agent loop is **not** hand-rolled: it is driven by **pydantic-ai** behind a swappable `AgentRuntimePort`, so coactra contributes the elegant surface + capability/MCP/A2A wiring, and pydantic-ai contributes the proven loop (tool calling, streaming, structured output, usage limits, timeouts, message history). North star ergonomics: the Cursor TS SDK.

## 2. Motivation and current gaps

`make_agent` exposes the seams (`mcp=`, `transport=`, six ports) but not the turnkey experience:

- **MCP is metadata-only** — mounting lists tool specs; no client, no `call_tool`; `FastMCPServer` (expose-as-MCP) is a stub.
- **A2A inbound is not bundled** — host hand-builds card + verifier + handler.
- **Config is "bring a constructed port,"** not declarative `{type, url}`.
- **No agent loop** — `Agent.think()` is one sync model call; nothing orchestrates model⇄tools.
- **Sync, text-only AI seam** — fine for one-shot `ask/structured`, wrong for an async streaming agent loop.

## 3. Goals / Non-goals

Goals:
- One declarative `Agent.create(...)` wiring model + MCP + A2A (in/out) + memory + workspace + organization + work.
- Async-first: `send → run.stream()/run.wait()`, `run(prompt, output_type=Schema)`, `call(peer, msg)`, `a2a_app()/serve()`.
- Loop powered by pydantic-ai behind `AgentRuntimePort` (swappable to openai-agents-sdk / LangGraph later).
- Full-auto defaults (capabilities-as-tools + auto-memory), all toggleable, with a safety floor (inbound verifier required; destructive tools via approval hook).
- v1 includes: timeouts, cancellation propagation, usage limits, approval enforcement hook, observability/trace hooks, message history.
- Strict backward compatibility: `make_agent` / `coactra.agent.Agent` unchanged.
- Offline-first defaults and tests (pydantic-ai `TestModel`/`FunctionModel`).

Non-goals (deferred):
- `Agent.resume(agent_id)` durable cross-process replay (v1 keeps in-process message history only).
- Synchronous wrapper.
- Swapping the runtime to LangGraph/openai-agents (kept possible by `AgentRuntimePort`).
- `Agent.prompt()` one-shot sugar.

## 4. Public API

`from coactra import Agent` (new facade; wraps internal `coactra.agent.Agent`).

### 4.1 Create (construction only — no network bind)

```python
agent = await Agent.create(
    model="anthropic/claude-sonnet-4-6",          # litellm id (required)
    instructions="You are an SRE triage assistant.",
    mcp={                                          # MCP tool servers (client)
        "docs": {"type": "http", "url": "https://…/mcp", "auth": {...}},
        "fs":   {"type": "stdio", "command": "npx", "args": [...]},
    },
    peers={"dba": {"url": "https://dba.internal"}},  # A2A outbound targets
    memory="graphiti",                            # or {"backend": "graphiti", "neo4j": {...}}
    workspace="local",                            # or {"backend": "daytona", ...} (stubs raise)
    organization={"backend": "sqlite", "url": …}, # roles/hierarchy → A2A policy + escalation
    work={"store": "sql", "url": …},              # durable work orders
    scope=Scope("acme", "agent:sre"),             # optional → Scope("local","agent"); REQUIRED for multi-tenant
    api_key=..., api_base=...,                     # litellm provider config
    autonomy="full",                              # "full" (default) | "safe" | "explicit"
    max_steps=12, request_limit=20, timeout_s=120,  # → pydantic-ai UsageLimits / model settings
    # escape hatches: runtime=, model_adapter=, policy=, verifier=, exchanger=, transport=, tools=[py fns]
)
```

Construction does no I/O beyond what backends require; **serving is a separate call** (§4.4).

### 4.2 Run / stream / structured

```python
run = await agent.send("triage the db latency incident")     # → Run handle
async for ev in run.stream():                                # typed events (carry run_id, seq, ts)
    match ev:
        case Assistant(text): ...
        case Thinking(text): ...
        case ToolCall(id, name, args): ...
        case ToolResult(id, name, result, error): ...
        case AgentCall(peer, question): ...        # A2A hop
        case AgentResult(peer, answer): ...
        case Usage(tokens, cost): ...
        case Status(state): ...                    # running | finished | error | cancelled
res = await run.wait()        # RunResult(status, text, output, tool_calls, usage, messages, error)
await run.cancel()            # cancels model stream + in-flight MCP/A2A calls

plan = await agent.run("give a 3-step plan", output_type=TriagePlan)   # typed (pydantic-ai native)
reply = await agent.call("dba", "is replication lagging?")            # A2A outbound by name
```

`output_type=` uses pydantic-ai's native structured output (validation + retries), not a post-hoc instructor pass. Per-`send` overrides (`model=`, `mcp=`, `autonomy=`) are **one-shot** (apply to that run only).

### 4.3 Capability methods (ergonomic surface)

```python
await agent.remember("primary db failover at 02:14");  facts = await agent.recall("db incidents", k=5)
await agent.workspace.write("notes/triage.md", "…");   text  = await agent.workspace.read("notes/triage.md")
out   = await agent.workspace.run("psql -c 'select 1'") # policy-gated exec
order = await agent.submit("Triage db latency");        st    = await agent.work.get(order.id)
if await agent.can("restart_db"): ...;                  boss  = await agent.manager
await agent.escalate(order, reason="needs DBA sign-off")
agent.enabled_tools()                                   # dry-run: every tool the model will see (incl. capability tools)
await agent.mount("name", {...})                        # mid-session MCP mount
```

`enabled_tools()` exists specifically so auto-registered capability tools are never hidden.

### 4.4 Serving / lifecycle

```python
app = agent.a2a_app(verifier=my_verifier)        # turnkey A2A inbound ASGI app (verifier REQUIRED)
await agent.serve(host="0.0.0.0", port=8016, verifier=my_verifier)
mcp_app = agent.mcp_app()                         # expose agent AS MCP server (later unit)

agent = await Agent.create(...)                  # create is a coroutine — await it
async with agent:                                # disposal closes MCP clients, A2A, backends
    run = await agent.send("…")
await agent.aclose()                             # explicit close
```

### 4.5 Events and results (DTOs)

Frozen, discriminated dataclasses in `coactra.agent.sdk`, each carrying `run_id`, `seq`, `ts` (and optional `trace_id`/`span_id`):
`Assistant(text)`, `Thinking(text)`, `ToolCall(id, name, args)`, `ToolResult(id, name, result, error)`, `AgentCall(peer, question)`, `AgentResult(peer, answer)`, `Usage(tokens, cost)`, `Status(state)`.
`RunResult(status, text, output, tool_calls, usage, messages, error)`.

## 5. Behavior: autonomy levels

`autonomy="full"` (default), `"safe"`, or `"explicit"`:

| | tools exposed to model | auto-memory | destructive tools (fs_write/run, work_submit, call_agent) |
|---|---|---|---|
| `full` (default) | all configured capabilities + MCP | on (recall before / remember after) | exposed, routed through approval hook (auto-approve green/yellow, red pauses) |
| `safe` | read-ish (recall, fs_read) + MCP | off | require explicit opt-in / approval policy |
| `explicit` | none (methods only) | off | methods only |

**Safety floor (applies at every level, including full):** A2A inbound requires a verifier (`a2a_app`/`serve` raise without one unless `verifier="none"` is passed explicitly + a loud warning); destructive tool calls pass through coactra's approval-tier resolver hook; `scope` defaults to local but is required for any multi-tenant/networked deployment (documented, warned).

Auto-memory reuses `coactra.workspace.integrations.memory`'s distiller.

## 6. Architecture

```
coactra/agent/sdk/
  facade.py      # Agent, Run, RunResult, event DTOs   ← re-exported as coactra.Agent
  runtime.py     # AgentRuntimePort + PydanticAIRuntime (default)
  config.py      # declarative dict/shorthand → backends (reuses make_coactra_agent)
  tools.py       # capability→tool bridge (MCP tools + memory/workspace/work/peer) over the mount registry
  mcp_client.py  # NEW MCP client (http + stdio) implementing MCPClientPort
  approval.py    # approval-tier gate wrapping destructive tool handlers
  serve.py       # turnkey A2A inbound app (card + required verifier)
  expose.py      # expose agent AS MCP server (later unit; un-stubs adapters/fastmcp.py)
lib-ai: coactra/ai/integrations/pydantic_model.py   # coactra-ai → pydantic-ai Model bridge
```

### 6.1 Runtime (`runtime.py`)

`AgentRuntimePort`: `run(messages, tools, *, output_type=None, limits, settings) -> RunResult` and `stream(...) -> AsyncIterator[Event]` and `cancel()`. Default `PydanticAIRuntime` builds a `pydantic_ai.Agent` from instructions + the tool registry, runs it, and **maps pydantic-ai's streaming nodes/events → coactra event DTOs**. pydantic-ai supplies the loop, tool-calling, structured output, `UsageLimits`, timeouts, retries, and `all_messages()` history. Swapping to openai-agents-sdk / LangGraph later = a new `AgentRuntimePort` impl, facade unchanged.

### 6.2 Model bridge (`lib-ai`)

Default model for the runtime is a **coactra-ai-backed pydantic-ai `Model`** so calls still go through litellm with coactra-ai's thinking-model handling (`reasoning_content` fallback, JSON-mode structured). This is a new `coactra.ai.integrations.pydantic_model` adapter — it does **not** alter the stable sync `Completer`/`Client`. (Alternative: point pydantic-ai at a litellm OpenAI-compatible proxy; the in-process Model adapter is preferred to avoid running a proxy.)

### 6.3 Capability→tool bridge (`tools.py`)

`Tool = {name, description, json_schema, handler}` derived from the existing `ToolSpec`/mount registry (qualified `<mount>.<tool>` names; no bare names). Sources: MCP via `MCPClientPort` (`list_tools` + `call_tool`); built-in capability tools (`recall`, `remember`, `workspace_read/write/run`, `work_submit`, `call_agent`) registered per `autonomy`. Destructive handlers receive `ToolCall.id` as an idempotency key and pass through `approval.py`. `call_agent` is handoff-style and goes through `PolicyGatedCollaborator` (deny-before-wire) + peer allowlist + depth/budget guard.

### 6.4 MCP client + A2A

- `mcp_client.py`: real client over the MCP SDK / FastMCP client (`{"type":"http"}` + `{"type":"stdio"}`), implementing `MCPClientPort`; lifecycle tied to `agent.aclose()`; `coactra-agent[mcp]` extra.
- `serve.py`: builds the a2a-sdk agent card (scope/role/instructions + tools) + **required** verifier + `build_a2a_app(handler=→agent.run)`. Outbound `peers` → `OfficialA2ATransport` (endpoint/audience resolvers from the dict) behind `PolicyGatedCollaborator` + organization policy; token exchange via configured `exchanger`.
- `expose.py`: un-stub `FastMCPServer` to publish the agent as `ask`/`run` MCP tools (later unit).

### 6.5 Cross-cutting

Errors → typed `CoactraError`/`ErrorCode` (tool failures → `ToolResult(error=…)`; A2A → `CollaborationDenied`; provider/timeout/validation via pydantic-ai). Timeouts/retries/usage limits via pydantic-ai settings surfaced on `create`/`send`. Cancellation (`run.cancel()`) propagates to the model stream and in-flight MCP/A2A calls. Observability: a tracing hook (pydantic-ai integrates with OTel/logfire) surfaced as an optional callback.

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

## 8. Backward compatibility & packaging

- `make_agent` / `coactra.agent.Agent` untouched; facade composes them.
- New deps: `pydantic-ai` (agent extra), MCP client/server (`coactra-agent[mcp]`). A2A deps via existing agent extras.
- Additive minor version bumps + changelog per `docs/RELEASE_POLICY.md`; public API registered in `docs/API_INDEX.md` / `public_api.json`.

## 9. Testing strategy (offline-first, security-first)

- pydantic-ai `TestModel`/`FunctionModel` drive the loop deterministically offline (scripted tool calls → final).
- **Deny-by-default security tests live in the first tool/loop unit, not last**: destructive tool requires approval; A2A inbound rejects without a verifier; cross-tenant `call_agent` denied.
- `MCPClientPort` conformance suite + a fake in-process MCP server.
- A2A inbound/outbound round-trip on existing fakes.
- `examples/elegant_agent.py` runs fully offline.
- CI: `coactra-agent[mcp]` + pydantic-ai lane.

## 10. Work units (sequenced, boundary-respecting)

1. **`coactra-ai`**: pydantic-ai `Model` bridge (`coactra.ai.integrations.pydantic_model`) + tests. (Does not touch the stable `Completer`.)
2. **`coactra-agent`**: `AgentRuntimePort` + `PydanticAIRuntime` (event mapping, limits, timeouts, cancel) over fakes — no MCP/A2A yet.
3. **`coactra-agent`**: `MCPClientPort` protocol + fake + conformance tests + deny/approval tests. *(split: 3a protocol+fake+tests, 3b http client, 3c stdio client, 3d `[mcp]` extra.)*
4. **`coactra-agent`**: `approval.py` gate (destructive-tool tier resolution) + security tests.
5. **`coactra-agent`**: `tools.py` capability→tool bridge over the mount registry (+ `enabled_tools()`).
6. **`coactra-agent`**: `facade.py` + `config.py` (`Agent.create/send/run/call`, declarative config via `make_coactra_agent`) over fakes; umbrella re-export **after** the surface is stable.
7. **`coactra-agent`**: A2A bundle — `serve.py` inbound (required verifier) *(split from)* outbound peers + `call_agent`.
8. **`coactra-agent`**: expose-as-MCP (`expose.py`, un-stub `FastMCPServer`) — after the core is proven.
9. **Docs/examples/CI**: `examples/elegant_agent.py`, API index, changelog, CI lane.

## 11. Open questions / future

- `Agent.resume(agent_id)` + a session/transcript store (persistence backend choice). v1 exposes `run.messages`/history in-process only.
- Sync wrapper over the async core.
- Alternate `AgentRuntimePort` impls (openai-agents-sdk, LangGraph durable) for users wanting handoffs/guardrails or durable resume.
- Full approval-tier enforcement UX (human-in-the-loop pause/resume on red) vs the v1 hook.
- Streaming token deltas (start message-level; add token deltas if needed).
