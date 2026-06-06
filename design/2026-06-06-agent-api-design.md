# Coactra Agent API — Design (alpha)

**Date:** 2026-06-06  **Status:** approved direction, pre-implementation  **Scope:** the public developer surface of `coactra` — one `Agent` door.

## Goal

A single public entry point — `from coactra import Agent` → `Agent.create(...)` — that a developer drives by **naming** things, never by constructing objects or injecting ports. The model is a string id; capabilities are names; tools (incl. MCP) are one list; A2A is a separate, default-on concern. `ai` is the internal engine behind the door. This is alpha: the deprecated layer is deleted, no back-compat.

## Public surface

```python
from coactra import Agent, Skill, oidc

agent = await Agent.create(
    model="claude-sonnet-4-5",        # model by id — routes through litellm + ai's thinking-model handling
    name="sre-1",                     # this agent's identity (peers reference each other by name)
    tenant="acme",                    # optional; defaults to "default"
    gateway="https://gateway/mcp",    # PRIMARY MCP path — tools sliced by the token's scopes
    auth=oidc(issuer, client_id, client_secret),  # token source (fetch+refresh); token=jwt for dev
    tools=[restart_service],          # local functions; an extra mcp("url") is the exception
    memory="graphiti",                # capability by name; automatic recall+remember (connector)
    workspace="./desk",               # optional; capability by path
    peers=["security-agent"],         # outbound A2A delegation targets (separate from tools)
    skills=[Skill("cert.rotate", description="Rotate TLS certs",
                  tags=["sre"], scopes=["cert:write"])],  # curated roster (string also OK); → Agent Card
    instructions="Be terse.",         # optional system prompt
    expose=True,                      # A2A expose — default on; publishes the Agent Card
)

answer = await agent.run("Restart nginx and confirm")          # text
plan   = await agent.run("Plan the migration", output=Plan)    # typed (Pydantic)
async for ev in agent.send("Investigate outage").stream():     # events
    ...   # Assistant · Thinking · ToolCall · ToolResult · Usage · Status
```

Helpers exported at top level: `Agent`, `oidc(...)` (token source), `Skill(...)` (structured roster entry), and `mcp(url)` for the exceptional local/extra server. **`gateway=`+`auth=` is the primary MCP path; `mcp(url)` is the exception.**

## Decisions (the locked forks)

1. **Tools are one unified list — functions and MCP are the same kind.** An MCP server is *translated into tools*; a bare function is one local tool, `mcp("url")` is a remote connection that expands into many. At the model layer they're identical, so they share `tools=`. `mcp()` is a 1-line tag (not an object) that marks "connect here and pull tools." No type-sniffing of bare strings. **Primary path:** `gateway=`+`auth=` — the token's scopes slice the available tools (no manual enumeration); an explicit `mcp(url)` is the exception for a local/extra server.

2. **Capabilities are named, not built.** `memory="graphiti"`, `workspace="./desk"` — same rule as `model=`. No object construction, no DI. An object escape-hatch may exist later but is never the default. (This is the explicit rejection of the old `make_agent(ai=AIPort(...))` ceremony.)

3. **Memory is automatic, implemented as a pure connector.** When `memory=` is set, the agent **auto-recalls** on the user's latest message and **auto-remembers** the turn — both by calling the backend's own `recall()`/`remember()`. coactra never ranks relevance, runs its own vector store, or judges salience; graphiti/mem0 own all of that. Rationale: the target worker model is small/cheap and will not reliably *choose* to call a recall tool, so recall must be automatic — but "automatic" lives in the agent's orchestration, not in a custom memory layer. coactra is the connector around the backend.

4. **A2A is separate from `tools=`.**
   - **Expose (inbound):** creating an agent makes it reachable via A2A **by default** (`expose=False` to opt out). Nothing to declare.
   - **Delegate (outbound):** a separate `peers=["name", ...]` list names the agents this one may call. Never mixed into `tools=`.

5. **Identity & scope are plain kwargs.** `name=` is the agent's identifier and lives in the same namespace `peers=` references. `tenant=` is optional (default `"default"`) for multi-tenant isolation. Consistent with "name it, don't build it" — no `Scope(...)` object at the public surface.

6. **Capability discovery = a curated roster, gated.** Each agent publishes a curated `skills=` roster — a string (simple) or structured `Skill(id, description, tags, scopes)` (the A2A Agent Card form), surfaced as an **Agent Card**. Authorized same-tenant peers read it to decide whom to delegate to. The raw tool list / argument schemas are **never** advertised. Security invariant: **seeing ≠ calling** — discovery exposes only the curated blurb, and every delegation is still auth-gated (token exchange + same-tenant policy). Ship order: peers-only first; add the published roster next.

## Internal / cut

- **Internal engine (kept, hidden):** `coactra.ai` — model calls via litellm + thinking-model handling (`reasoning_content` fallback, TOOLS→JSON), embeddings, reasoning capture/replay. Users never import it; `Agent` and the planner use it. Optional later: rename `ai`→`models`/`llm` for clarity (carries a brownfield cost — homelab imports `coactra.ai` — so behind a compat alias, deferred).
- **Cut (no consumer, deleted in alpha):** `make_agent`, the ports-based `Agent` facade, `mounting.py` + `begin_turn()` mid-session mounting, the sync collaboration stack (`NullTransport`, sync `PolicyGatedCollaborator`), `AIPort` + `FakeAI`. Verified unused — homelab deliberately avoids this layer.
- **Kept because homelab consumes it:** `coactra.ai` (internal), the **async** A2A collaboration stack (`AsyncPolicyGatedCollaborator`, `AllowSameTenant`, `AgentRef`, `CollaborationDenied`), the a2a adapters (`OfficialA2ATransport`, `a2a_server`, `make_a2a_executor`), `KeycloakExchanger`. The new `Agent` builds its A2A expose/peers on top of these adapters.

## Security

Capability advertisement is separate from authorization. The only thing discoverable is the curated `skills=` roster (string or structured `Skill`); raw tools/args/endpoints are never published (that would be a reconnaissance surface). Knowing an agent *can* do X never implies the right to make it do X — outbound delegation goes through token exchange and the same-tenant collaboration policy.

## Works today vs target

**Today (in `coactra.agent.sdk`):** `Agent.create(model, tools=[functions], instructions, output_type)`, `run` / `send().stream()` / `wait()`, litellm routing + thinking-model handling via `LiteLLMModel`, rich streamed result.

**Target (to build):**
- top-level `from coactra import Agent, mcp`
- `mcp()` tag + `tools=` expanding MCP servers into tools
- `memory=` automatic connector (auto-recall + auto-remember)
- `workspace=`, `peers=`, `name=`, `tenant=`, `skills=`, `expose=`
- `output=` as the alias for `output_type=`
- A2A expose default-on; `peers=` outbound delegation over the existing async adapters
- curated capability roster (after peers-only ships)

## Out of scope (this spec)

Auto-recall tuning (what query, where injected — sane defaults only); the full capability-card wire protocol beyond a curated blurb; the `jobs`/workflow expansion (planner → triage/routing) — its own design session; migrating homelab off any kept symbols.
