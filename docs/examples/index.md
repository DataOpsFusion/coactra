# Examples

The examples are small and runnable. They show the intended Coactra style:
application behavior is written as plain functions, while classes stay at durable
state and backend boundaries.

## Start Here

| Goal | Example |
|---|---|
| Smallest normal app | [Basic Incident Triage](basic-incident-triage.md) |
| Explicit composition with plain functions | [Composed Support Agent](composed-support-agent.md) |
| Higher-level SDK shape | [Offline Agent SDK](offline-agent-sdk.md) |
| Scoped support memory | [Customer Support Memory](customer-support-memory.md) |
| Agent + work + memory (project) | [Support Desk](support-desk.md) |
| **Work orders (focused scripts)** | [Work Order Lifecycle](work-order-lifecycle.md) |
| **Procedure-backed work** | [Procedure-Backed Work](procedure-backed-work.md) |
| Durable work lifecycle (project) | [Release Runner](release-runner.md) |
| Workspace files and handoff | [Workspace Research Desk](workspace-research-desk.md) |
| Policy-gated collaboration | [Multi-Agent Policy](multi-agent-policy.md) |

## Local Setup

Install the package editable when running examples from a checkout:

```bash
python -m pip install -e "./coactra[all,dev]"
```

Run examples from the repository root. Each page lists its exact command and the
production boundary it is meant to demonstrate.
