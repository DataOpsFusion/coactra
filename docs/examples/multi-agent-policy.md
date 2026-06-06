# Multi-Agent Policy

A `Team` is a bag of agents plus a policy that decides who may talk to whom.
By default only same-tenant agents may communicate. This example shows Team
construction and policy enforcement.

## Demonstrates (Runnable)

- `Team([agent_a, agent_b])` — registry with default same-tenant policy
- `agent.card` — curated skills roster (the Agent Card)
- Same-tenant access allowed; cross-tenant access denied by default

## Code (Runnable)

```python
import asyncio
from coactra import Agent, Team, Skill


async def main() -> None:
    # Two agents in the same tenant — same-tenant talk is allowed
    sre = await Agent.create(
        model="claude-haiku-4-5",
        name="sre-agent",
        tenant="acme",
        token="dev-token",
        skills=[Skill("infra.restart", description="Restart infrastructure services",
                      tags=["sre"], scopes=["infra:write"])],
        instructions="You manage infra.",
    )

    security = await Agent.create(
        model="claude-haiku-4-5",
        name="security-agent",
        tenant="acme",
        token="dev-token",
        skills=[Skill("cert.rotate", description="Rotate TLS certificates",
                      tags=["security"], scopes=["cert:write"])],
        instructions="You handle security.",
    )

    # Team: registry + same-tenant policy (default)
    team = Team([sre, security])

    # Inspect the curated capability roster
    print("SRE skills:", sre.card)
    print("Security skills:", security.card)
    print("Team members:", [a.name for a in team])


if __name__ == "__main__":
    asyncio.run(main())
```

---

!!! warning "Designed — not yet shipped"
    **Outbound A2A peer delegation** — one agent actually *calling* another agent
    over the wire — requires `peers=` and the A2A serving layer, which ship as part
    of the **Workflow** / A2A milestone.

    When peers ship, the pattern will be:

    ```python
    # designed — not yet runnable
    sre = await Agent.create(
        ...,
        peers=["security-agent"],   # outbound delegation targets
    )
    # sre can then ask security-agent for help during a run
    ```

    The same-tenant policy is enforced even then: cross-tenant delegation is denied
    before the wire is touched.

## Policy Rules

| Caller tenant | Target tenant | Result |
|---|---|---|
| `acme` | `acme` | Allowed (same-tenant) |
| `acme` | `other-corp` | Denied — `CollaborationDenied` |

Custom policies (OpenFGA / AuthZEN) plug in at the Team level when you need
finer-grained access control.

## Production Notes

| Concern | Dev default | Production |
|---|---|---|
| Auth | `token="dev-token"` | `auth=oidc(issuer, client_id, client_secret)` |
| Policy | Same-tenant (default) | OpenFGA / AuthZEN adapter |
| A2A transport | — | `OfficialA2ATransport` (when peers ship) |
