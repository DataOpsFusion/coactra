# Example Catalog

Run examples from the repository root after installing the package:

```bash
python -m pip install -e "./coactra[all,dev]"
```

Start here:

```bash
python3 examples/incident_response_handoff.py
python3 examples/projects/ticket_triage/app.py
python3 examples/work/change_approval_gate.py
```

| If you want to see... | Read | Source |
|---|---|---|
| the smallest normal app | [Incident Response Handoff](../examples/incident-response-handoff.md) | `examples/incident_response_handoff.py` |
| explicit port composition | [Support Ticket Agent](../examples/support-ticket-agent.md) | `examples/support_ticket_agent.py` |
| the optional SDK loop | [Offline SRE Agent](../examples/offline-sre-agent.md) | `examples/offline_sre_agent.py` |
| repeat-issue memory | [Resolution Memory](../examples/resolution-memory.md) | `examples/projects/resolution_memory/` |
| agent + memory + work | [Ticket Triage](../examples/ticket-triage.md) | `examples/projects/ticket_triage/` |
| durable release work | [Release Work Lifecycle](../examples/release-work-lifecycle.md) | `examples/work/` |
| procedure-backed work | [Procedure Runbook](../examples/procedure-runbook.md) | `examples/work/procedure_runbook.py` |
| release project layout | [Release Checkpoint](../examples/release-checkpoint.md) | `examples/projects/release_checkpoint/` |
| scoped workspace files | [Research Workspace](../examples/research-workspace.md) | `examples/projects/research_workspace/` |
| collaboration policy | [Approval Routing](../examples/approval-routing.md) | `examples/projects/approval_routing/` |

Examples use local defaults. For production, replace the backend or adapter:
`SqlWorkStore` for durable work, mem0/Graphiti for memory, a real AI port for
model calls, and verified A2A adapters for service-to-service collaboration.
