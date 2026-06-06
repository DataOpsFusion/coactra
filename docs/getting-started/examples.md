# Example Catalog

Use this page to choose the sample closest to what you are building. Each example
has a focused page in the Examples section, plus a source link for copying the
actual runnable file.

## Run From The Repo

Install the local checkout once:

```bash
python -m pip install -e "./coactra[all,dev]"
```

Then run examples from the repository root:

```bash
python3 examples/basic_incident_triage.py
python3 examples/work/lifecycle_with_approval.py
```

## Recommended Starting Points

| If you are building... | Start here | Source |
|---|---|---|
| a normal single-agent app | [Basic Incident Triage](../examples/basic-incident-triage.md) | [source](https://github.com/DataOpsFusion/coactra/blob/main/examples/basic_incident_triage.py) |
| explicit function-first composition | [Composed Support Agent](../examples/composed-support-agent.md) | [source](https://github.com/DataOpsFusion/coactra/blob/main/examples/function_first_agent.py) |
| a higher-level SDK loop | [Offline Agent SDK](../examples/offline-agent-sdk.md) | [source](https://github.com/DataOpsFusion/coactra/blob/main/examples/elegant_agent.py) |
| support or helpdesk memory | [Customer Support Memory](../examples/customer-support-memory.md) | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/customer_support_memory) |
| combined helpdesk (agent + work + memory) | [Support Desk](../examples/support-desk.md) | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/support_desk) |
| durable jobs or releases | [Work Order Lifecycle](../examples/work-order-lifecycle.md) | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/work) |
| procedure-backed work orders | [Procedure-Backed Work](../examples/procedure-backed-work.md) | [source](https://github.com/DataOpsFusion/coactra/blob/main/examples/work/procedure_backed_work.py) |
| release project layout | [Release Runner](../examples/release-runner.md) | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/release_runner) |
| a file-backed agent desk | [Workspace Research Desk](../examples/workspace-research-desk.md) | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/workspace_research_desk) |
| multi-agent collaboration | [Multi-Agent Policy](../examples/multi-agent-policy.md) | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/multi_agent_policy) |

## Naming Style

Docs examples use a small naming convention:

| Prefix | Use for |
|---|---|
| `make_*` | local port factories and backend adapters |
| `build_*` | composition roots that assemble ports and facades |
| `submit_*` | durable work creation |
| `draft_*` | model-generated first-pass output |
| `triage_*`, `run_*`, `handle_*` | application behavior |

Application behavior should stay function-first:

```python
def triage_incident(agent, work, incident: str):
    ...
```

Use classes when they own durable state or an external boundary, such as
`WorkManager`, `SqlWorkStore`, memory backends, workspace backends, A2A transports,
or OAuth/Keycloak exchangers.
