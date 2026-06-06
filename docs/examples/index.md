# Examples

The examples are scenario-first. Each one runs offline unless the page explicitly
mentions an optional extra.

Install from a checkout before running them:

```bash
python -m pip install -e "./coactra[all,dev]"
```

| Scenario | Example |
|---|---|
| Smallest incident app | [Incident Response Handoff](incident-response-handoff.md) |
| Agent composed from plain ports | [Support Ticket Agent](support-ticket-agent.md) |
| Optional SDK loop with no network call | [Offline SRE Agent](offline-sre-agent.md) |
| Durable release work | [Release Work Lifecycle](release-work-lifecycle.md) |
| Human approval gate | [Release Work Lifecycle](release-work-lifecycle.md) |
| Procedure-backed runbook | [Procedure Runbook](procedure-runbook.md) |
| Repeat-issue memory | [Resolution Memory](resolution-memory.md) |
| Agent + memory + work project | [Ticket Triage](ticket-triage.md) |
| Release checkpoint project | [Release Checkpoint](release-checkpoint.md) |
| Scoped workspace files | [Research Workspace](research-workspace.md) |
| Policy-gated collaboration | [Approval Routing](approval-routing.md) |

These are not production deployments. They use in-memory stores, local fake ports,
and ephemeral workspaces so the behavior is visible without service setup. The
production replacement point is always the backend or adapter boundary, not the
application function.
