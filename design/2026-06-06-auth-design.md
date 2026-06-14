# Coactra Auth And Identity Design

**Status:** current Team-first alpha contract.

## Goal

Coactra is an OAuth/OIDC client and MCP-gateway consumer, not an identity
provider, gateway, or authorization server. It consumes scoped credentials,
advertises curated capabilities, and delegates fine-grained authorization to the
policy seam.

## Model

- **Token** carries identity and scopes.
- **Gateway** slices available MCP tools to the token's scopes.
- **Agent Card** advertises curated effective skills and security schemes.
- **Policy** decides whether a requested action is allowed, denied, or requires approval.

## Team-first shape

```python
team = Team(scope=Scope.local(), policy=policy)
agent = await team.add_agent(
    name="sre-agent",
    model_capability="fast-chat",
    gateway="https://gateway/mcp",
    auth=token_source,
    skills=[...],
    expose=True,
)
```

## Decisions

1. **Gateway is the primary MCP path.**
   - the token slices tool access
   - additive local functions or extra MCP mounts remain secondary

2. **Coactra is a consumer/connector, not the authority.**
   - no token issuance
   - no gateway ownership
   - no built-in authorization engine

3. **Policy is the fine-grained seam.**
   - same-tenant defaults are only one possible policy profile
   - OpenFGA/AuthZEN/custom host authorizers remain pluggable

4. **Agent Cards are curated capability manifests.**
   - skills and security schemes are visible
   - credentials and raw tool power are not

5. **Identity source remains pluggable.**
   - static tokens for dev
   - OAuth/OIDC token sources in production
   - future workload-identity schemes remain adapter concerns
