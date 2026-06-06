# Procedure-Backed Work

!!! warning "Designed — not yet shipped"
    This page describes capability-routing in the **Workflow** layer. The resolver
    and Team matcher are finalized in
    [design/2026-06-06-workflow-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-workflow-design.md)
    and
    [design/2026-06-06-team-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-team-design.md).
    Code shown here is the **intended API** — it will not run against the current release.

A Workflow step can target an agent by **capability** (`needs=`) instead of by
name (`agent=`). The Team's matcher resolves the best agent from its roster at
runtime — keyword/tag match by default, embedding similarity on request.

## What This Enables

- Steps declare *what* they need, not *who* does it
- The Team picks the right agent from the registered roster
- Agents can be swapped or added without touching the playbook
- Ties resolve by first-match or Team-defined priority

## Intended API (designed)

```python
# designed — not yet runnable
import asyncio
from coactra import Agent, Team, Workflow, step, Skill


async def main() -> None:
    sre = await Agent.create(
        model="claude-sonnet-4-5",
        name="sre-agent",
        tenant="acme",
        auth=oidc(issuer, client_id, client_secret),
        gateway="https://gateway/mcp",
        skills=[Skill("infra.restart", description="Restart infra services",
                      tags=["sre", "infra"])],
    )

    security = await Agent.create(
        model="claude-sonnet-4-5",
        name="security-agent",
        tenant="acme",
        auth=oidc(issuer, client_id, client_secret),
        gateway="https://gateway/mcp",
        skills=[Skill("cert.rotate", description="Rotate TLS certs",
                      tags=["security", "certs"])],
    )

    # Keyword match (default) — no embedding model required
    team = Team([sre, security])

    play = Workflow("cert-rotation-deploy", steps=[
        step("rotate the production cert", needs="certs"),      # → security-agent
        step("verify cert chain", needs="certs"),               # → security-agent
        step("redeploy web tier", needs="infra"),               # → sre-agent
        step("final sign-off", approve=True),
    ])

    run = await play.run(team, durable=True)
    print("Done:", run.status)


asyncio.run(main())
```

## Matcher Options

| Option | Resolver | Use when |
|---|---|---|
| `Team([...])` | Keyword/tag match | Deterministic; no model required |
| `Team([...], match="semantic")` | Embedding similarity | Fuzzy natural-language needs |
| `step(..., agent="name")` | Pinned — trivial match | You know exactly who does it |

## See Also

- [Work Order Lifecycle](work-order-lifecycle.md) — the durable run model
- [Multi-Agent Policy](multi-agent-policy.md) — who-may-talk policy (runnable now)
- [Workflow design spec](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-workflow-design.md)
