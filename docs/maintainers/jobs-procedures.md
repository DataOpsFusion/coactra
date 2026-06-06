# Workflow Design

`coactra.jobs` / `coactra.orchestration` / `coactra.work` are being consolidated
and renamed as `coactra.workflow`. A **Workflow** is a playbook of steps plus the
manager that runs it across the Team — durably, with retries and approval pauses.
"Work order / job / durable orchestration" are properties of a Workflow running,
not separate things.

**Key principles:**

- `Workflow("name", steps=[step(...)])` — authored playbook; runs directly, no planning
- `Workflow.run_goal("goal", team=team)` — triage: reuse saved playbook or plan new
- Planner output is a **candidate** — never auto-saved; promoted after review or N successes
- Durable execution delegated to LangGraph (default) / Temporal / Prefect
- Approvals are a step property (`approve=True`); run pauses durably and resumes
- Internal run ledger: `Playbook`, `WorkflowRun`, `Step`, `Approval`, `Checkpoint`
- Public surface: `Workflow`, `step()`, `Workflow.run_goal()`

The authoritative spec — triage model, assignment resolver, resilience decisions,
data-core format, and the rename mechanics — is the workflow design document:

**[design/2026-06-06-workflow-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-workflow-design.md)**

The rename migration from `jobs`/`work`/`orchestration` → `workflow` and
`directory` → `team` is documented in:

**[design/2026-06-06-rename-migration.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-rename-migration.md)**
