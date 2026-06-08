# Release Runner

A release pipeline as an authored Workflow: each stage is a `step`, human
sign-offs are approval pauses, and the whole run is durable — it survives
restarts, records a checkpoint at each stage, and resumes from the last good
checkpoint after a failure.

## Code

```python
import asyncio
from coactra import Agent, StaticToken, Skill, Team, Workflow
from coactra.workflow import step


async def main(version: str) -> None:
    release_eng = await Agent.create(
        model="claude-sonnet-4-5",
        name="release-eng",
        tenant="acme",
        auth=StaticToken("gateway-token"),  # or authlib TokenSource in production
        gateway="https://gateway/mcp",
        skills=[Skill("release.pipeline", description="Run release stages",
                      tags=["release", "deploy"])],
    )

    team = Team([release_eng])

    play = Workflow(f"release-{version}", steps=[
        step("run pre-release checks and tests",  agent="release-eng"),
        step("build and push artifacts",          agent="release-eng"),
        step("deploy to staging",                 agent="release-eng"),
        step("staging validation sign-off",       approve=True),
        step("deploy to production",              agent="release-eng"),
        step("smoke-test production",             agent="release-eng"),
        step("release manager sign-off",          approve=True),
        step("tag release and close",             agent="release-eng"),
    ])

    run = await play.run(team, durable=True)
    print(f"Release {version} → {run.status}")


asyncio.run(main("v1.4.2"))
```

## Durable Guarantees

| Property | Behaviour |
|---|---|
| Restart safety | Run resumes from the last checkpoint (LangGraph checkpointer) |
| Approval pause | Run halts durably; resumes when a human approves |
| Retry | Failed steps retry per step/policy configuration |
| Audit trail | Every stage transition logged to the internal run ledger |

## Engine Options

The Workflow layer delegates durability to a pluggable engine:

| Engine | `resume_semantics` | Notes |
|---|---|---|
| LangGraph (default) | same-thread | Requires persistent checkpointer in production |
| Temporal | same-thread | Hard durable; signals/replay; recommended for critical pipelines |
| Prefect | new-run-with-prior-state | Deployment-triggered; host-implemented resume |

## See Also

- [Work Order Lifecycle](work-order-lifecycle.md) — the run/approval/checkpoint model
- [Procedure-Backed Work](procedure-backed-work.md) — capability routing
- [Workflow design spec](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-workflow-design.md)
