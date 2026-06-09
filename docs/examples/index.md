# Examples

These examples show the current Coactra **Team · Agent · Workflow** model. Runnable examples use features that are built and ship today.

## Runnable Today

| Goal | Example |
|---|---|
| Smallest Team-first app | [Basic Incident Triage](basic-incident-triage.md) |
| Agent with tools + instructions | [Offline Agent SDK](offline-agent-sdk.md) |
| Agent + automatic memory | [Customer Support Memory](customer-support-memory.md) |
| Agent + workspace desk | [Workspace Research Desk](workspace-research-desk.md) |
| Agent + memory + tools | [Support Desk](support-desk.md) |
| Team routing + explicit policy | [Multi-Agent Policy](multi-agent-policy.md) |
| Team composition with skills | [Composed Support Agent](composed-support-agent.md) |
| Durable work with approval | [Work Order Lifecycle](work-order-lifecycle.md) |
| Procedure-backed steps | [Procedure-Backed Work](procedure-backed-work.md) |
| Release pipeline with checkpoints | [Release Runner](release-runner.md) |

## Local Setup

```bash
pip install coactra[agent]
```

For a development checkout:

```bash
pip install -e "./coactra[all,dev]"
```

Pass `auth="dev-token"` or `auth=StaticToken(...)` in `team.add_agent(...)` calls. For OAuth client-credentials in production, use `authlib` or `httpx-oauth` and pass the resulting `TokenSource` to `auth=`. See [Getting Started](../getting-started/quickstart.md) for the full quickstart.
