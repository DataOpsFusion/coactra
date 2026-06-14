# Coactra Workflow Design

**Status:** current Team-first alpha contract.

## Goal

A `Workflow` is a reusable process that runs across a `Team`. It binds steps to
exact skills or explicit agents, carries approvals and checkpoints, records runs,
and delegates durability to external runtime engines.

## Public shape

```python
from coactra import Workflow
from coactra.workflow import step

play = Workflow(
    "rotate-cert",
    steps=[
        step("rotate the prod cert", requires_skill="cert.rotate"),
        step("redeploy", agent="sre-1", approve=True),
    ],
)

await play.run(team)
await Workflow.run_goal("rotate prod cert and redeploy", team)
```

## Decisions

1. **Capability routing uses exact skill ids.**
   - `requires_skill=` is the default routing field
   - `agent=` is the explicit override
   - free-text workflow requirement strings are removed from the public contract

2. **Workflow owns process, not identity.**
   - Team owns which agents exist
   - Workflow declares required capability and transition structure

3. **Planner output is candidate process, not automatic truth.**
   - known goals can reuse stored playbooks
   - new goals can be planned
   - planner output should be promoted deliberately, not auto-saved as canonical workflow truth

4. **Durability is delegated outward.**
   - Coactra owns workflow vocabulary and run semantics
   - LangGraph, Temporal, Prefect, or other engines own execution guarantees

5. **Approvals and checkpoints are first-class.**
   - approval-gated transitions pause durably
   - resume semantics are explicit
   - run state remains observable and replayable

## Internal model

- `Playbook` / workflow definition
- `WorkflowRun` / execution instance
- `StepResult`
- `Approval`
- checkpoint state
- planner and playbook-store seams

## Connector boundaries

- Coactra owns workflow data model, Team routing hooks, approvals, and run records.
- Engines own durable execution and restart guarantees.
- planners and stores remain swappable seams.
