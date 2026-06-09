# Work Order Lifecycle

A **Workflow run** is the durable unit of work: it survives restarts, pauses for approvals, retries failed steps, and stores its full audit trail.

## What Ships with Workflow

- `Workflow("name", steps=[...])` — authored playbook
- `step("description", agent=, requires_skill=, approve=)` — step builder
- `Workflow.run_goal("goal text", team=team)` — triage: reuse saved or plan new
- Approval pauses and resume
- Internal run ledger: `WorkflowRun`, `Checkpoint`, `Approval`

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, StaticToken, Team, Workflow
from coactra.workflow import step


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="deploy"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="deploy",
                profile=ModelProfile(
                    name="deploy",
                    model="openai/qwen3.6-plus",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    await team.add_agent(
        model_capability="deploy",
        name="sre-agent",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=["infra.restart", "deployment"],
        expose=True,
    )

    play = Workflow("deploy-service", steps=[
        step("validate config and run pre-checks", requires_skill="general"),
        step("deploy to staging", agent="sre-agent"),
        step("manager sign-off", approve=True),
        step("deploy to production", agent="sre-agent"),
        step("verify and close", agent="sre-agent"),
    ])

    run = await team.run(play)
    print("Status:", run.status)


asyncio.run(main())
```

## Lifecycle Stages

```
submitted → running → [paused for approval] → resumed → done
                                                       → failed → retried
                                                       → cancelled
```

## Run Goal (triage mode)

```python
run = await Workflow.run_goal(
    "rotate prod cert and redeploy web tier",
    team=team,
)
```

Planned playbooks are saved as **candidates** — promoted to the reusable library only after review or repeated success.
