# Examples

These examples show the Coactra **Agent · Team · Workflow** model. Runnable examples
use only features that are built and ship today. Pages marked **Designed — coming**
describe the Workflow layer that is designed but not yet shipped.

## Runnable Today

| Goal | Example |
|---|---|
| Smallest agent app | [Basic Incident Triage](basic-incident-triage.md) |
| Agent with tools + instructions | [Offline Agent SDK](offline-agent-sdk.md) |
| Agent + automatic memory | [Customer Support Memory](customer-support-memory.md) |
| Agent + workspace desk | [Workspace Research Desk](workspace-research-desk.md) |
| Agent + memory + tools | [Support Desk](support-desk.md) |
| Team routing + same-tenant policy | [Multi-Agent Policy](multi-agent-policy.md) |
| Agent composition with skills | [Composed Support Agent](composed-support-agent.md) |

## Designed — Coming

These pages describe the **Workflow** layer (durable playbooks, approval pauses,
triage/planner). The data model and decisions are finalized; implementation follows.

| Goal | Example |
|---|---|
| Durable work with approval | [Work Order Lifecycle](work-order-lifecycle.md) |
| Procedure-backed steps | [Procedure-Backed Work](procedure-backed-work.md) |
| Release pipeline with checkpoints | [Release Runner](release-runner.md) |

## Local Setup

```bash
pip install coactra
```

For a development checkout:

```bash
pip install -e ".[all,dev]"
```

Pass `token="dev-token"` or `auth=oidc(...)` in every `Agent.create()` call. See
[Getting Started](../getting-started/quickstart.md) for the full quickstart.
