# Naming Migration

Coactra consolidated seven distributions into one `coactra` package. Old import
paths remain as compatibility shims; new code should use the canonical names below.

## Package Names

| Old (deprecated shim) | Canonical | Install |
|---|---|---|
| `coactra.orchestration` | `coactra.jobs` | base package |
| `coactra.work` | `coactra.jobs.work` | base package |
| `coactra.workflow` | `coactra.jobs.workflow` | base package |
| `coactra.organization` | `coactra.directory` | base package |

```python
# Before (still works)
from coactra.orchestration.work import WorkManager

# After (preferred)
from coactra.jobs import WorkManager
```

## Scope Types

| Import | Use for |
|---|---|
| `coactra.jobs.Scope` or `WorkScope` | Work orders |
| `coactra.jobs.WorkflowScope` | Stored procedures |
| `coactra.scope.CoactraScope` | Apps composing multiple packages |
| `coactra.agent.Scope` | Agent facade |
| `coactra.memory.Scope` | Memory recall/write |
| `coactra.workspace.Scope` | Agent desk files |

When an app uses several packages, start from `CoactraScope` and call
`to_work_kwargs()`, `to_agent_kwargs()`, etc.

## Repository Layout

```
coactra/                    # single distribution
  src/coactra/
    ai/ memory/ workspace/ agent/ jobs/ directory/   # canonical
    orchestration/ work/ workflow/ organization/     # compat shims
  tests/
    ai/ memory/ workspace/ agent/ jobs/ directory/   # matches modules
examples/
  work/                       # focused work-order scripts
  projects/                   # small runnable apps
docs/                         # MkDocs site
```

## Examples and Docs

- Work scripts: `examples/work/`
- Runnable projects: `examples/projects/` (e.g. `ticket_triage` for agent + work + memory)
- Operations guide: [Work Orders](../operations/work-orders.md)

Shims will be removed only after a published deprecation window. homelab-mcp and
other consumers can migrate imports dependency-first without a flag day.
