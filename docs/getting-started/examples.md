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
python3 examples/incident_response_handoff.py
python3 examples/work/release_work_lifecycle.py
```

## Recommended Starting Points

| If you are building... | Start here | Source |
|---|---|---|
| a normal single-agent app | [Incident Response Handoff](../examples/incident-response-handoff.md) | [source](https://github.com/DataOpsFusion/coactra/blob/main/examples/incident_response_handoff.py) |
| explicit function-first composition | [Support Ticket Agent](../examples/support-ticket-agent.md) | [source](https://github.com/DataOpsFusion/coactra/blob/main/examples/support_ticket_agent.py) |
| a higher-level SDK loop | [Offline SRE Agent](../examples/offline-sre-agent.md) | [source](https://github.com/DataOpsFusion/coactra/blob/main/examples/offline_sre_agent.py) |
| support or helpdesk memory | Resolution Memory | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/resolution_memory) |
| combined helpdesk (agent + work + memory) | Ticket Triage | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/ticket_triage) |
| durable jobs or releases | [Work Order Lifecycle](../examples/work-order-lifecycle.md) | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/work) |
| procedure-backed work orders | [Procedure-Backed Work](../examples/procedure-backed-work.md) | [source](https://github.com/DataOpsFusion/coactra/blob/main/examples/work/procedure_runbook.py) |
| release project layout | Release Checkpoint | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/release_checkpoint) |
| a file-backed agent desk | Research Workspace | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/research_workspace) |
| multi-agent collaboration | Approval Routing | [source](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/approval_routing) |

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
