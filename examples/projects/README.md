# Sample Projects

Small runnable projects with concrete names and local defaults.

Install from the repository root:

```bash
python -m pip install -e "./coactra[all,dev]"
```

| Project | Shows | Run |
|---|---|---|
| `resolution_memory` | remember and recall prior fixes | `python3 examples/projects/resolution_memory/app.py` |
| `ticket_triage` | agent draft + work lifecycle + ticket memory | `python3 examples/projects/ticket_triage/app.py` |
| `release_checkpoint` | release work checkpoints and artifacts | `python3 examples/projects/release_checkpoint/app.py` |
| `research_workspace` | scoped files, handoff, capability manifest | `python3 examples/projects/research_workspace/app.py` |
| `approval_routing` | policy-gated collaboration before A2A transport | `python3 examples/projects/approval_routing/app.py` |

These are local examples, not production deployments. Replace memory backends,
work stores, AI ports, workspace backends, and A2A verifiers at the adapter
boundary.
