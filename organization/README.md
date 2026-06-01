# organization

> Charter only — captures the problem + vision. Full design comes later.

## The problem it solves

There's no standalone, **multi-tenant** model of a fleet of agents — who belongs to
which tenant, how they're isolated, and (optionally) how they're structured. Today
this is custom glue inside the app.

## The vision

A multi-tenant fleet model with three things: **isolation, tenancy, and (real)
hierarchy.** Flat fleet is the simplest baseline, but hierarchy is a **first-class,
actively-used feature** — you use it to carve out **dedicated spaces** (e.g. a
standing R&D group always testing and looking for improvements) and to define who
reports/escalates to whom. Tenant isolation keeps each tenant's fleet separate.

Structure stays *configurable* (flat ↔ structured), but hierarchy isn't an
afterthought — it's how you give a part of the fleet a dedicated mission.

```python
org.role("platform")           # what this seat does
org.reports_to("dev")          # the chain of command
org.escalate(work_order)       # push it up a tier
```

## Wraps (swappable backends)

sqlmodel for persistence; role concepts seen in crewai / autogen / langgraph-supervisor,
but those **bake structure into execution** — this is a standalone directory.

## Verdict (from research — see ../RESEARCH-VERDICTS.md)

**BUILD a thin standalone model.** CrewAI hierarchical process and LangGraph Supervisor
exist but bake org into the *execution* graph; a standalone multi-tenant directory is a
real gap. Build only: tenants, groups/departments, roles/seats, memberships (human /
service / agent), reporting edges, escalation routes, versioned policy references.
**Do NOT put workflow execution inside `organization`** — it answers "who owns this?"
and "where does escalation go?", nothing more.

## Open design points (later)

- Boundary vs the `agent` runtime (org = structure, agent = behavior).
- Dynamic hiring / org changes at runtime.
