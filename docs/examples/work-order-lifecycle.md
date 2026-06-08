# Work Order Lifecycle

A **Workflow run** is the durable unit of work: it survives restarts, pauses for
approvals, retries failed steps, and stores its full audit trail. "Work order /
job / orchestration" are properties of a Workflow running — not separate things.

## What Ships with Workflow

- `Workflow("name", steps=[...])` — authored playbook
- `step("description", agent=, needs=, approve=)` — step builder
- `Workflow.run_goal("goal text", team=team)` — triage: reuse saved or plan new
- Durable execution via LangGraph (default) / Temporal / Prefect
- Approval pauses: run halts until a human resolves, then resumes
- Internal run ledger: `WorkflowRun`, `Checkpoint`, `Approval`

## Code

```python
import asyncio
from coactra import Agent, StaticToken, Team, Workflow
from coactra.workflow import step


async def main() -> None:
    sre = await Agent.create(
        model="claude-sonnet-4-5",
        name="sre-agent",
        tenant="acme",
        auth=StaticToken("gateway-token"),
        gateway="https://gateway/mcp",
        skills=["infra restart", "deployment"],
    )

    team = Team([sre])

    # Authored playbook — runs directly, no planning step
    play = Workflow("deploy-service", steps=[
        step("validate config and run pre-checks", needs="deployment"),
        step("deploy to staging", agent="sre-agent"),
        step("manager sign-off", approve=True),          # pauses for human
        step("deploy to production", agent="sre-agent"),
        step("verify and close", agent="sre-agent"),
    ])

    # durable=True → uses LangGraph checkpointing (Temporal swappable)
    run = await play.run(team, durable=True)
    print("Run ID:", run.id, "Status:", run.status)


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
# triage: runs saved playbook if goal is known; plans + saves candidate if new
run = await Workflow.run_goal(
    "rotate prod cert and redeploy web tier",
    team=team,
    durable=True,
)
```

Planned playbooks are saved as **candidates** — promoted to the reusable library
only after review or N successful runs (never auto-saved, preventing library
self-poisoning with bad generated plans).

## See Also

- [Procedure-Backed Work](procedure-backed-work.md) — steps assigned by capability
- [Release Runner](release-runner.md) — pipeline with checkpoints
- [Workflow design spec](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-workflow-design.md)
