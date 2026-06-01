# agent

> Charter only — captures the problem + vision. Full design comes later.

## The problem it solves

**Corrected after verifying the protocols against primary sources** — they're more
capable than first assumed. The gap is the **composition/policy layer above them**, not
the protocols themselves:
1. **A2A is mature**, not "dumb" (v1.0.1, 2026 — tasks, multi-turn contexts, streaming,
   push notifications, artifacts). Build *collaboration policy* on top; do NOT fork it.
2. **MCP already supports live tool changes** — `tools.listChanged` (MCP 2025-11-25),
   FastMCP live mounting, OpenAI Agents SDK re-lists per run + `invalidate_tools_cache()`.
   The real gap: mount a capability *mid-session*, apply policy, resolve naming
   conflicts, invalidate caches, expose it on the next safe model turn.
3. **Human auth exists; delegated identity needs careful wiring** — MCP OAuth
   on-behalf-of is real, but **token passthrough is explicitly forbidden**. Use RFC 8693
   token exchange (subject/actor chains); never pass a human token through agents/servers.

## The vision

The runtime that wires the other libraries (`lib-ai`, `memory`, `workspace`,
`workflow`, `organization`, `work`) into a working agent — as a **composition/policy layer over
mature protocols**, not a reinvention of them. Richer agent collaboration = policy on
top of A2A; mid-session capability mounting = orchestration on top of MCP
`tools.listChanged`; human action = delegated on-behalf-of identity (RFC 8693).

```python
agent.mount_mcp(server, effective="next_turn")  # hot-mount, expose on next safe turn
agent.act_on_behalf_of(delegation_grant)         # delegated identity, NOT token passthrough
```

## Wraps (swappable backends)

openai-agents-sdk, a2a-sdk (v1.0.x), fastmcp, MCP OAuth + RFC 8693 token exchange.

## Verdict (from research — see ../RESEARCH-VERDICTS.md)

**WRAP the protocols + BUILD a thin composition/policy layer.** A2A and MCP already do
the hard transport work. Don't fork them. Your gap is real but narrower: session-level
orchestration (mid-session mount → next-safe-turn exposure, conflict/cache handling) +
**delegated identity via RFC 8693** (never token passthrough).

## Open design points (later)

- Mid-session mount → "next safe turn" exposure: where exactly is the turn boundary?
- Delegated-identity chain (RFC 8693 subject/actor) across multi-hop delegation.
- Collaboration policy above A2A: who may talk to whom, when.

## Integrated Coactra stack

The core package stays independently usable with ports and in-process defaults. When the
sibling capability packages are installed, use the optional integration helper:

```python
from coactra.agent.integrations import make_coactra_agent
```

`make_coactra_agent(...)` translates the sibling scope shapes and injects the real AI,
memory, workspace, workflow, organization, and work facades into `Agent`.
