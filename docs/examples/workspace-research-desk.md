# Workspace Research Desk

Use this when an agent needs a place to keep files and handoff notes between
steps or sessions.

## Demonstrates

- `open_workspace(...)`
- scoped files
- handoff and day-note files
- passive capability manifests
- no local command execution by default

## Run

```bash
python3 examples/projects/workspace_research_desk/app.py
```

Production services should use a sandbox-backed workspace adapter instead of
local filesystem storage for untrusted tenants.

Source: [https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/workspace_research_desk](https://github.com/DataOpsFusion/coactra/tree/main/examples/projects/workspace_research_desk)
