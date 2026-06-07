# Improvement Backlog

This backlog tracks implementation gaps and quality improvements for the current
**Agent · Team · Workflow** architecture. The design decisions are finalized in
the `design/2026-06-06-*.md` specs; this page tracks the work still outstanding
against those decisions.

## Current Milestone: Agent Core

Status of built features (0.0.x):

| Feature | Status |
|---|---|
| `Agent.create(model, tools, instructions, output)` | Built |
| `run / send().stream()` | Built |
| `agent.card` | Built |
| `Team` (registry + keyword matcher + same-tenant policy) | Built |
| `memory="inprocess\|mem0\|graphiti"` | Built |
| `workspace=` (file tools) | Built |
| `gateway=` + `auth=oidc(...)` primary MCP path | Built |
| `skills=[Skill(...)]` structured roster | Built |

## Outstanding: Agent Core

- `peers=` outbound A2A delegation targets
- Full A2A serving (`expose=True` beyond card publish)
- `match="semantic"` embedding-based Team matcher
- Memory guardrails: injection cap, deletion/export (GDPR), write policy
- Workspace `run` allow-list configuration surface

## Outstanding: Workflow Layer

- `Workflow(steps=[...])` authored playbook
- `step()` helper + YAML loader
- `Workflow.run_goal()` triage (reuse / plan / candidate)
- Planner (`ai.structured` goal → playbook)
- Playbook store + similarity matcher for triage
- Durable engine wiring (LangGraph default; Temporal/Prefect adapters)
- Approval pause/resume (`approve=True` step property)
- Internal run ledger: `WorkflowRun`, `Checkpoint`, `Approval`

## Authoritative Design Sources

| Area | Spec |
|---|---|
| Agent API | [design/2026-06-06-agent-api-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-agent-api-design.md) |
| Auth / identity | [design/2026-06-06-auth-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-auth-design.md) |
| Team | [design/2026-06-06-team-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-team-design.md) |
| Workflow | [design/2026-06-06-workflow-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-workflow-design.md) |
| Review refinements | [design/2026-06-06-review-refinements.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-review-refinements.md) |
| Vision / build order | [design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md) |
| Implementation plan | [design/2026-06-06-implementation-plan-agent-core.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-implementation-plan-agent-core.md) |
