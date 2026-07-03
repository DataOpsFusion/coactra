# Procedure-Backed Work

A Workflow step should usually target a broad **skill id** (`requires_skill=`) plus optional
`required_tags=` selectors. The Team resolves the effective agent from its roster at runtime.
If multiple agents share the same broad skill and no selector makes the match unique, routing
fails closed.

## What This Enables

- Steps declare the capability domain they need, not a hardcoded worker name
- `required_tags` disambiguates overlapping specialists without exploding the skill taxonomy
- The Team enforces routing and policy instead of relying on registration order
- `agent=` remains available as an explicit override when a specific worker must act

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
                capability="security",
                profile=ModelProfile(name="security", model="openai/deepseek-v4-pro", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
            ),
            ModelRoute(
                capability="ops",
                profile=ModelProfile(name="ops", model="openai/deepseek-v4-pro", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
            ),
        ]),
    )
    await team.add_agent(
        model_capability="security",
        name="cert-operator",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=[Skill("security", description="Operate certificate changes", tags=["certs", "execute"])],
        expose=True,
    )
    await team.add_agent(
        model_capability="security",
        name="cert-reviewer",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=[Skill("security", description="Review certificate work", tags=["certs", "review"])],
        expose=True,
    )
    await team.add_agent(
        model_capability="ops",
        name="web-ops",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=[Skill("ops", description="Operate the web tier", tags=["deploy", "execute"])],
        expose=True,
    )

    play = Workflow("cert-rotation-deploy", steps=[
        step("rotate the production cert", requires_skill="security", required_tags=["certs", "execute"]),
        step("review cert evidence and chain", requires_skill="security", required_tags=["certs", "review"]),
        step("redeploy web tier", requires_skill="ops", required_tags=["deploy", "execute"]),
        step("final human sign-off", approve=True, approval_only=True),
    ])

    run = await team.run(play)
    print("Done:", run.status)


asyncio.run(main())
```

## Matcher Options

| Option | Resolver | Use when |
|---|---|---|
| `team.match_skill("security", required_tags=["review"])` | Broad skill plus tag disambiguation | Multiple specialists share the same domain |
| `team.match_skill("security")` | Fail-closed unique match | Exactly one agent advertises that skill |
| `step(..., agent="name")` | Pinned | You know exactly who must do the work |

## Approval Notes

- `approve=True` pauses the workflow and requires `Workflow.resume(..., proof_bundle=...)` evidence to continue.
- `approval_only=True` makes that step a pure human gate; no agent runs after approval.

## See Also

- [Work Order Lifecycle](work-order-lifecycle.md) - the durable run model
- [Code Change Workflow](code-change-workflow.md) - thin implement/verify/review builder
- [Multi-Agent Policy](multi-agent-policy.md) - who-may-talk policy
- [Workflow design spec](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-workflow-design.md)
