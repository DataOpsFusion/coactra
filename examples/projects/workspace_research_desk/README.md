# Workspace Research Desk

Use this when an agent needs a place to keep files and handoff notes between steps or sessions.

What it demonstrates:

- `open_workspace(...)`
- scoped files
- handoff/day-note
- passive capability manifests
- no local command execution by default

Run from the repo root:

```bash
PYTHONPATH=workspace/src python3 examples/projects/workspace_research_desk/app.py
```

Production swap: use a sandbox-backed workspace adapter instead of local filesystem storage for untrusted tenants.
