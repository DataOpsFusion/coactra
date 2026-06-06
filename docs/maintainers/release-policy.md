# Release Policy

Coactra is currently at **alpha** (`0.0.x`). The alpha phase covers the Agent core
milestone. No backward-compatibility guarantees are made while the public surface
is being established. Each milestone (Agent → workspace → Team → Workflow) ships
as a minor version increment.

## Alpha Surface (0.0.x)

The deprecated layer (`make_agent`, ports-based Agent, sync collaboration stack)
has been deleted in the alpha redesign. No compat shims during alpha.

Public exports:

```python
from coactra import Agent, Team, Skill, oidc, mcp
```

Anything not exported from `coactra` directly is internal and may change at any time.

## Stability Tiers (target for v1)

| Tier | Meaning | Allowed changes |
|---|---|---|
| `stable` | Preferred public API | No breaking change without deprecation window |
| `beta` | Public but may change before v1 | Changes allowed with changelog + migration note |
| `experimental` | Useful but not compatibility-promised | May change between minor releases |
| `compatibility` | Old import path / migration alias | Keep until removal window closes |
| `internal` | Implementation detail | Can change anytime |

## Preferred Import Root (v1 target)

```
from coactra import Agent, Team, Workflow, Skill, step, oidc, mcp
```

Old paths (`coactra.jobs`, `coactra.directory`, `coactra.orchestration`) will be
kept as compatibility aliases during the migration window and removed in a later
release per the rename migration plan.

## Adapter Maturity vs API Stability

An adapter can be import-stable but operationally experimental. Track both:

- **API stability** — can the constructor/import contract change?
- **Adapter maturity** — is the backend suitable for production?

## Runtime Resume Semantics

Every workflow engine adapter declares one of:

| Value | Meaning |
|---|---|
| `same-thread` | `resume(id, ...)` continues the same durable execution |
| `new-run-with-prior-state` | Resume starts a new run carrying previous state |
| `unsupported` | Adapter can start but cannot resume |
| `host-owned` | Coactra passes through; host code owns real resume behavior |

## Rename Migration

The authoritative source for rename mechanics (`jobs`/`work`/`orchestration` →
`workflow`; `directory`/`organization` → `team`):

**[design/2026-06-06-rename-migration.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-rename-migration.md)**

System vision and build order:

**[design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md)**
