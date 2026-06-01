# fleetlib.agent — v0.2 (clean composition root, ports, DSA)

> `agent` is the runtime that WIRES the other libs into a working agent. Verdict stands:
> WRAP the mature protocols (A2A, MCP, OpenAI Agents SDK, MCP OAuth) + BUILD a thin
> composition/policy layer — do NOT fork the protocols. v0.2 goal: a **clean, wrappable
> interface** (so a2a/openai-sdk wrap it trivially), proper **DI + factory + composition
> root**, and the right **DSA** for the two real mechanisms (mount namespacing, identity
> chain). Keep what v0.1 got right (tenant-qualified deniable collaboration, RFC-8693
> no-passthrough); clean up the structure.

## Locked principles
- **Ports + DI.** The five siblings are consumed through narrow `Protocol` PORTS
  (`AIPort`, `MemoryPort`, `WorkspacePort`, `WorkflowPort`, `OrganizationPort`) — the
  agent NEVER imports sibling code. Ports are **injected** via a composition root.
- **Ports mirror the real sibling facades** so wiring is a 3-line adapter, not glue:
  - `MemoryPort.remember(events, scope) / recall(query, scope, k) -> list[...]` ← matches `fleetlib.memory`
  - `OrganizationPort.can(member, action) / members(node) / manager(node)` ← matches `fleetlib.organization`
  - `AIPort.ask(...) / structured(...)`, `WorkflowPort.run(procedure, state)`, `WorkspacePort.read/write/run`.
  Real wiring lives OUTSIDE this lib (or in an optional `bindings` extra); the core ships
  Protocol + in-process fakes so it's testable with zero siblings installed.
- **Factory / composition root:** `make_agent(*, scope, ai=…, memory=…, workspace=…, workflow=…, organization=…, mcp=…, transport=…, exchanger=…, policy=…)` wires everything; sensible in-process defaults; nothing instantiated inline.
- **Clean wrappable surface:** small, typed, async-first where the protocols are async; a
  plain `Agent` facade an openai-sdk tool / a2a skill can wrap in a few lines.

## The two real mechanisms (DSA)
1. **Mid-session MCP mounting** — `MountRegistry`:
   - **prefix-trie / namespaced map** for tool-name conflict resolution (`<mount>.<tool>`),
     O(prefix) lookup, deterministic conflict policy.
   - a small **state machine** per mount: `pending → active`, promoted only at an
     observable `begin_turn()` boundary (tools change between turns, never mid-turn), with
     cache invalidation. `agent.mount_mcp(server, effective="next_turn")`.
2. **Delegated identity** — RFC-8693 token exchange:
   - an **actor chain** (immutable linked list of subject→actor hops); `act_on_behalf_of(grant)` / `delegate_further(...)`; a raw human/subject token is NEVER passed through downstream (enforced + tested).

## Collaboration (keep v0.1, clean it)
- Tenant-qualified `AgentRef(tenant_id, agent_id)` targets; `CollaborationPolicy` can DENY
  cross-tenant talk (deny-before-allow). `PolicyGatedCollaborator` structurally satisfies
  `fleetlib.workflow`'s `Collaborator`/`EscalationRouter` Protocols (so it drops into a
  workflow run with no adapter) — verify signatures against the built workflow lib.

## Layers
```
domain/        # Scope, AgentRef, ToolSpec, DelegationGrant, ExchangedIdentity — plain types
ports/         # AIPort/MemoryPort/WorkspacePort/WorkflowPort/OrganizationPort Protocols + in-process fakes
mounting.py    # MountRegistry (trie namespacing + pending→active state machine + invalidation), MCPServerPort
identity.py    # TokenExchanger Protocol + InProcessExchanger (actor chain, no passthrough)
collaboration.py # AgentRef, CollaborationPolicy, AllowSameTenant, PolicyGatedCollaborator, A2ATransportPort
agent.py       # Agent facade (begin_turn / mount_mcp / act_on_behalf_of / talk / recall …)
factory.py     # make_agent(...) composition root
```

## Boundary / tests
- No protocol forking; real SDKs (fastmcp/a2a/openai-agents/keycloak) stay raise-on-use
  optional-extra stub adapters. Core is testable with only pydantic.
- TDD. Keystone tests (mutation-worthy): mount invisible until `begin_turn`; raw subject
  token never reaches downstream; cross-tenant talk denied (genuine two-tenant AgentRefs);
  port wiring via fakes; factory DI. Keep the v0.1 suite green where the shape is preserved.
