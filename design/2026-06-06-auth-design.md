# Coactra Auth & Identity — Design (alpha)

**Date:** 2026-06-06  **Status:** approved direction, pre-implementation.  **Grounding:** aligned to the 2026 industry direction (MCP OAuth 2.1 + A2A Agent Cards) — see sources.

## Goal

coactra is an **OAuth 2.1 client + MCP-gateway consumer**, not an auth system. An agent presents a token; a gateway slices its tools to the token's scopes; the agent advertises curated skills via an A2A Agent Card. coactra does **not** issue tokens, run the gateway, or implement the policy engine — it consumes the standards everyone else is building.

## Model

- **Token (JWT / OAuth 2.1):** carries identity (`sub` → name, tenant) + **scopes**. Short-lived. The blessed MCP path (OAuth 2.1, PKCE, RFC 8707 resource indicators, RFC 9728 AS discovery).
- **Gateway (one MCP endpoint):** verifies the token and **slices the tool list** to what the scopes allow ("tool slicing"). coactra lists the gateway's tools *with its token* → that filtered set **is** the agent's tools. **No manual MCP enumeration.**
- **Agent Card (A2A):** a discoverable manifest — name, **skills** (+ which scope each needs), `securitySchemes`. **Credentials are never in the card.** Published when `expose=True`; peers fetch it to discover skills and how to authenticate. This is the roster (decision ⑥), standardized.
- **Token source (pluggable):** static `token=` (dev), OIDC client-credentials **fetch + auto-refresh** (`auth=oidc(...)`), or workload identity (SPIFFE) later. Short-lived favored; never hardcode creds in the runtime.
- **Fine-grained authz (policy seam):** scopes are coarse; the Team/directory policy decides who-may-do-what, and can delegate to OpenFGA / OpenID AuthZEN / Cedar. Default: same-tenant.

## Public surface

```python
agent = await Agent.create(
    model="claude-sonnet-4-5",
    gateway="https://gateway/mcp",                 # one endpoint
    auth=oidc(issuer, client_id, client_secret),   # fetch+refresh  (or token=jwt for dev)
    # name / tenant  ← token claims
    # tools          ← gateway-sliced set for these scopes  (+ local funcs / mcp() additive)
    skills="cert rotation, vault, secrets",        # → published as the Agent Card (curated)
)
```

## Decisions

1. **Standard split (chosen):** token = scopes → gateway slices tools; Agent Card = curated skills. Aligns coactra with MCP OAuth 2.1 + A2A so it interoperates with the gateways/IdPs the ecosystem is standardizing on.
2. **coactra = consumer/connector** of those standards.
3. **Token source pluggable; short-lived favored; no creds in the runtime.**
4. **Fine-grained = policy seam** (same-tenant default; OpenFGA/AuthZEN pluggable).
5. **Identity seam pluggable** — OAuth/OIDC now; SPIFFE / verifiable-delegation (AIP) later. Don't marry one scheme; agent identity is still an open frontier (NIST initiative).

## Amends to earlier specs

- **Agent:** `mcp()`-per-server → `gateway=` + `auth=`/`token=` (one entry, scope-sliced); local funcs / extra `mcp()` stay additive. `name`/`tenant` read from token claims (kwargs override for dev). `skills=` is published as the **Agent Card**, not a JWT claim. `expose=True` publishes the card.
- **Team:** who-may-talk = the **policy seam** (same-tenant default → OpenFGA/AuthZEN). Peer **discovery = fetch the peer's Agent Card**.

## Connector boundaries

- **Owns:** OAuth 2.1 client flow wiring; listing gateway tools with a token; Agent Card publish/fetch; the token-source seam; the policy seam.
- **Delegates:** token issuance → Keycloak/IdP; tool filtering → the gateway; fine-grained policy → OpenFGA/AuthZEN; workload identity → SPIFFE.
- **Never:** issues tokens, runs the gateway, or implements an authorization engine.

## Today vs target

**Today (`coactra.agent`):** `KeycloakExchanger` (RFC 8693 token exchange), `OfficialA2ATransport` / `a2a_server`, `AllowSameTenant` policy, `AsyncTokenExchanger`, `CachedAsyncTokenExchanger`.

**Target:** an OAuth 2.1 client + gateway tool-list consumer; Agent Card publish/fetch; a pluggable token source (OIDC client-credentials fetch+refresh helper — replaces homelab's hand-rolled token provider); a policy seam with an OpenFGA/AuthZEN adapter.

## Out of scope (this spec)

Being the gateway or the AS; implementing SPIFFE/WIMSE; the AIP verifiable-delegation protocol (tracked for later as the identity frontier settles).

## Sources (industry direction, 2026)

- MCP Authorization spec (OAuth 2.1, PKCE, RFC 8707/9728): https://modelcontextprotocol.io/specification/draft/basic/authorization
- MCP 2026-07-28 release candidate (auth aligns to OAuth/OIDC): https://blog.modelcontextprotocol.io/posts/2026-07-28-release-candidate/
- A2A Agent Card (skills + securitySchemes + per-skill scopes; no creds): https://agent2agent.info/docs/concepts/agentcard/ ; https://a2a-protocol.org/latest/topics/enterprise-ready/
- Enterprise MCP gateways / tool slicing: https://www.truefoundry.com/blog/enterprise-mcp-access-control ; https://obot.ai/blog/mcp-access-control-tool-level-permissions/
- Fine-grained authz for agents (scopes insufficient → policy layer): https://workos.com/blog/best-authorization-platforms-ai-agent-permissions-2026
- NIST AI agent identity/authz initiative: https://www.nccoe.nist.gov/sites/default/files/2026-02/accelerating-the-adoption-of-software-and-ai-agent-identity-and-authorization-concept-paper.pdf
- AIP — verifiable delegation across MCP & A2A: https://arxiv.org/pdf/2603.24775
- IETF AI-agent auth draft: https://www.ietf.org/archive/id/draft-klrc-aiagent-auth-00.html
