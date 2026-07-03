# Multi-Agent Policy

`Team` is an explicit coordination root: it requires a `Scope` and a `Policy`, then owns agent registration, rostering, and workflow routing. Collaboration remains deny-before-wire, but permissive behavior must be chosen deliberately.

## Demonstrates

- `Team(scope=..., policy=..., model_resolver=...)` — explicit coordination boundary
- `agent.card` — curated skills roster
- same-tenant delegation allowed explicitly with `Policy.permissive()`
- `peers=[agent]` and `peers=[RemotePeer(...)]` create outbound delegation tools

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, RemotePeer, Scope, Skill, Team


async def main() -> None:
    resolver = ModelResolver([
        ModelRoute(
            capability="sre",
            profile=ModelProfile(name="sre", model="openai/deepseek-v4-pro", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
        ),
        ModelRoute(
            capability="security",
            profile=ModelProfile(name="security", model="openai/deepseek-v4-pro", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
        ),
        ModelRoute(
            capability="orchestrator",
            profile=ModelProfile(name="orchestrator", model="openai/deepseek-v4-pro", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
        ),
    ])
    team = Team(
        scope=Scope(tenant_id="acme", namespace="ops"),
        policy=Policy.permissive(),
        model_resolver=resolver,
    )
    sre = await team.add_agent(
        model_capability="sre",
        name="sre-agent",
        auth="dev-token",
        skills=[Skill("ops", description="Restart infrastructure services", tags=["sre", "execute"], scopes=["infra:write"])],
        instructions="You manage infra.",
        expose=True,
    )
    security = await team.add_agent(
        model_capability="security",
        name="security-agent",
        auth="dev-token",
        skills=[Skill("security", description="Review security-sensitive infrastructure changes", tags=["review", "tls"], scopes=["cert:write"])],
        instructions="You handle security.",
        expose=True,
    )

    print("SRE card:", sre.card)
    print("Security card:", security.card)
    print("Roster:", team.roster())

    caller = await team.add_agent(
        model_capability="orchestrator",
        name="orchestrator",
        auth="dev-token",
        peers=[security],
    )
    await caller.run("Ask the security peer to review this cert rotation.")

    remote_caller = await team.add_agent(
        model_capability="orchestrator",
        name="remote-orchestrator",
        auth="dev-token",
        peers=[
            RemotePeer(
                name="security-agent",
                endpoint="https://security.example/a2a",
                audience="security-agent",
                tenant="acme",
            )
        ],
    )
    await remote_caller.run("Ask the security peer for the current exception policy.")


if __name__ == "__main__":
    asyncio.run(main())
```

## Peer Forms

| Peer form | Behavior |
|---|---|
| `peers=[security_agent]` | In-process `ask_security_agent` tool calling `security_agent.run(...)`. |
| `peers=[RemotePeer(...)]` | A2A transport-backed `ask_security_agent` tool. |
| `peers=["security-agent"]` | Creates the documented tool name and reports unavailable until a registry or remote config is supplied. |

## Policy Rules

| Caller tenant | Target tenant | Result |
|---|---|---|
| `acme` | `acme` | Allowed when your policy permits it. |
| `acme` | `other-corp` | Denied before the wire is touched by policy checks. |

Custom policies such as OpenFGA or host authorizers can plug in at the Team/policy seam when you need finer-grained authorization.

## Production Notes

| Concern | Dev default | Production |
|---|---|---|
| Policy | `Policy.permissive()` | guarded / approval-gated / OpenFGA-backed policy |
| Auth | `auth="dev-token"` | `StaticToken` or authlib/httpx-oauth `TokenSource` |
| A2A transport | In-process Agent peer | `RemotePeer(...)` over `OfficialA2ATransport` |
