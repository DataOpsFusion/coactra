# Naming Migration

Coactra is renaming its internal modules to match the three-noun public model:
**Agent · Team · Workflow**. This page maps old names to new names and explains the
migration path.

!!! warning "Alpha — no back-compat shims"
    Coactra 0.0.x is alpha. The renames break imports; there are **no compatibility
    shims** in the alpha series. Update imports when you update the package version.

## Module renames

| Old name | New name | Concept |
|----------|----------|---------|
| `coactra.directory` | `coactra.team` | Roster of agents, who-may-talk policy |
| `coactra.organization` | *(dropped)* | Merged into Team |
| `coactra.jobs` | `coactra.workflow` | Playbook, durable step execution |
| `coactra.work` | *(dropped)* | Merged into Workflow |
| `coactra.orchestration` | *(dropped)* | Merged into Workflow |

The renames bring the module layout in line with the public surface (`from coactra import Agent`, `Team`, `Workflow`).

## Import migration table

### Directory → Team

```python
# Before
from coactra.directory import Organization, OrgStore
from coactra.organization import Organization

# After
from coactra.team import Team
```

### Jobs / Work / Orchestration → Workflow

```python
# Before
from coactra.jobs import WorkManager, WorkOrder
from coactra.jobs.workflow import Procedure, WorkflowEngine
from coactra.work import WorkManager
from coactra.orchestration import DurableOrchestrator

# After
from coactra.workflow import Workflow, step
```

## Top-level imports (the one door)

After the rename, the full public surface is at the top level:

```python
from coactra import Agent          # available now
from coactra import Skill          # available now
from coactra import oidc           # available now
from coactra import StaticToken    # available now
from coactra import mcp            # available now
from coactra import Team           # designed / coming
from coactra import Workflow, step # designed / coming
```

Homelab and other consumers currently import `coactra.directory` and
`coactra.jobs.workflow`. Those imports will break when the rename ships. The migration
is import-only — no behavioral changes.

## Old compatibility shims (pre-alpha-rename)

Before the renames land, the following shims still exist in the package but carry no
back-compat promise:

| Shim path | Points to | Remove when |
|-----------|-----------|-------------|
| `coactra.work` | `coactra.jobs.work` | Team/Workflow rename ships |
| `coactra.orchestration` | `coactra.jobs.workflow` | Team/Workflow rename ships |
| `coactra.organization` | `coactra.directory` | Team rename ships |

Do not write new code against these paths.

## Repository layout (target)

```
coactra/
  src/coactra/
    ai/           # internal engine
    agent/        # Agent facade + SDK (the one door)
    team/         # Team (formerly directory + organization)
    workflow/     # Workflow (formerly jobs + work + orchestration)
    memory/       # memory backend connector
    workspace/    # workspace capability
  tests/
docs/
examples/
design/           # specs (authoritative for public surface)
```
