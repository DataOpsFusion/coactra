# Multi-Agent Policy

A `Team` is a bag of agents plus a policy that decides who may talk to whom. By default only same-tenant agents may communicate. This example shows Team construction, capability discovery, and outbound peer delegation.

## Demonstrates

- `Team([agent_a, agent_b])` — registry with default same-tenant policy
- `agent.card` — curated skills roster, formatted as the Agent Card
- Same-tenant access allowed; cross-tenant access denied by default
- `peers=[agent]` and `peers=[RemotePeer(...)]` create outbound A2A-style delegation tools

## Code

```python
import asyncio
from coactra import Agent, RemotePeer, Team, Skill


async def main() -> None:
    sre = await Agent.create(
        model="claude-haiku-4-5",
        name="sre-agent",
        tenant="acme",
        auth="dev-token",
        skills=[Skill("infra.restart", description="Restart infrastructure services",
                      tags=["sre"], scopes=["infra:write"])],
        instructions="You manage infra.",
    )

    security = await Agent.create(
        model="claude-haiku-4-5",
        name="security-agent",
        tenant="acme",
        auth="dev-token",
        skills=[Skill("cert.rotate", description="Rotate TLS certificates",
                      tags=["security"], scopes=["cert:write"])],
        instructions="You handle security.",
    )

    team = Team([sre, security])
    print("SRE card:", sre.card)
    print("Security card:", security.card)
    print("Roster:", team.roster())

    caller = await Agent.create(
        model="claude-haiku-4-5",
        name="orchestrator",
        tenant="acme",
        auth="dev-token",
        peers=[security],
    )
    await caller.run("Ask the security peer to review this cert rotation.")

    remote_caller = await Agent.create(
        model="claude-haiku-4-5",
        name="remote-orchestrator",
        tenant="acme",
        auth="dev-token",
        peers=[RemotePeer(
            name="security-agent",
            endpoint="https://security.example/a2a",
            audience="security-agent",
            tenant="acme",
        )],
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

The same-tenant policy is enforced before local calls or remote A2A sends.

## Policy Rules

| Caller tenant | Target tenant | Result |
|---|---|---|
| `acme` | `acme` | Allowed by default. |
| `acme` | `other-corp` | Denied before the wire is touched. |

Custom policies such as OpenFGA or AuthZEN can plug in at the Team/policy seam when a host needs finer-grained authorization.

## Production Notes

| Concern | Dev default | Production |
|---|---|---|
| Auth | `auth="dev-token"` | `auth=oidc(token_url, client_id, client_secret)` |
| Policy | Same-tenant default | OpenFGA / AuthZEN adapter |
| A2A transport | In-process Agent peer | `RemotePeer(...)` over `OfficialA2ATransport` |
