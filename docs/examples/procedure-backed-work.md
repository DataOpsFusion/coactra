# Procedure-Backed Work

A Workflow step can target an agent by exact **skill id** (`requires_skill=`) instead of by name (`agent=`). The Team resolves the effective agent from its roster at runtime.

## What This Enables

- Steps declare *what capability package* they require, not *who* performs the work
- The Team picks an agent with the required effective skill
- Agents can be swapped or added without touching the playbook
- `agent=` remains available as an explicit override

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, StaticToken, Skill, Team, Workflow
from coactra.workflow import step


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="ops"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="sre",
                profile=ModelProfile(name="sre", model="openai/qwen3.6-plus", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
            ),
            ModelRoute(
                capability="security",
                profile=ModelProfile(name="security", model="openai/qwen3.6-plus", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
            ),
        ]),
    )
    await team.add_agent(
        model_capability="sre",
        name="sre-agent",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=[Skill("infra.restart", description="Restart infra services", tags=["sre", "infra"])],
        expose=True,
    )
    await team.add_agent(
        model_capability="security",
        name="security-agent",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=[Skill("cert.rotate", description="Rotate TLS certs", tags=["security", "certs"])],
        expose=True,
    )

    play = Workflow("cert-rotation-deploy", steps=[
        step("rotate the production cert", requires_skill="cert.rotate"),
        step("verify cert chain", requires_skill="cert.rotate"),
        step("redeploy web tier", agent="sre-agent"),
        step("final sign-off", approve=True),
    ])

    run = await team.run(play)
    print("Done:", run.status)


asyncio.run(main())
```

## Matcher Options

| Option | Resolver | Use when |
|---|---|---|
| `team.match_skill("cert.rotate")` | Exact skill-id match | Stable capability routing |
| Team-owned fuzzy/semantic routing | Future adapter seam | Not part of the current Team-first execution path |
| `step(..., agent="name")` | Pinned | You know exactly who does it |

## See Also

- [Work Order Lifecycle](work-order-lifecycle.md) — the durable run model
- [Multi-Agent Policy](multi-agent-policy.md) — who-may-talk policy
- [Workflow design spec](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-workflow-design.md)
