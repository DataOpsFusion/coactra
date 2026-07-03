# Work Order Lifecycle

A **Workflow run** is the durable unit of work: it survives restarts, pauses for approvals,
retries failed steps, and stores its full audit trail.

## What Ships with Workflow

- `Workflow("name", steps=[...])` - authored playbook
- `step("description", agent=, requires_skill=, required_tags=, approve=, approval_only=)` - step builder
- `Workflow.run_goal("goal text", team=team)` - triage: reuse saved or plan new
- Approval pauses and resume with `ProofBundle` evidence
- Internal run ledger: `WorkflowRun`, `Checkpoint`, `Approval`

## Code

```python
import asyncio
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, StaticToken, Skill, Team, Workflow
from coactra.workflow import ProofBundle, VerificationReceipt, step


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="deploy"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(
                capability="ops",
                profile=ModelProfile(
                    name="ops",
                    model="openai/deepseek-v4-pro",
                    api_base="https://opencode.ai/zen/go/v1",
                    api_key=os.environ["OC_KEY"],
                ),
            )
        ]),
    )
    await team.add_agent(
        model_capability="ops",
        name="ops-implementer",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=[Skill("ops", description="Execute deployments", tags=["execute", "deploy"])],
        expose=True,
    )
    await team.add_agent(
        model_capability="ops",
        name="ops-reviewer",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=[Skill("ops", description="Review deployment evidence", tags=["review", "deploy"])],
        expose=True,
    )

    play = Workflow("deploy-service", steps=[
        step("validate config and run pre-checks", requires_skill="ops", required_tags=["execute"]),
        step("deploy to staging", requires_skill="ops", required_tags=["execute"]),
        step("review staging evidence", requires_skill="ops", required_tags=["review"]),
        step("manager sign-off", approve=True, approval_only=True),
        step("deploy to production", requires_skill="ops", required_tags=["execute"]),
        step("verify and close", requires_skill="ops", required_tags=["execute"]),
    ])

    run = await team.run(play)
    print("Status:", run.status)

    if run.status == "interrupted":
        run = await play.resume(
            run,
            team,
            decision={
                "approved": True,
                "proof_bundle": ProofBundle(
                    summary="staging checks passed and change ticket approved",
                    receipts=[
                        VerificationReceipt(
                            command="make smoke",
                            exit_code=0,
                            stdout_sha256="abc123",
                        )
                    ],
                ),
            },
        )
        print("Resumed:", run.status)


asyncio.run(main())
```

## Lifecycle Stages

```
submitted -> running -> [paused for approval] -> resumed -> done
                                                       -> failed -> retried
                                                       -> cancelled
```

## Run Goal (triage mode)

```python
run = await Workflow.run_goal(
    "rotate prod cert and redeploy web tier",
    team=team,
)
```

Planned playbooks are saved as **candidates** - promoted to the reusable library only after review or repeated success.
