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

## Design verdict

**BUILD a thin standalone model.** CrewAI hierarchical process and LangGraph Supervisor
exist but bake org into the *execution* graph; a standalone multi-tenant directory is a
real gap. Build only: tenants, groups/departments, roles/seats, memberships (human /
service / agent), reporting edges, escalation routes, versioned policy references.
**Do NOT put workflow execution inside `organization`** — it answers "who owns this?"
and "where does escalation go?", nothing more.

## Open design points (later)

- Boundary vs the `agent` runtime (org = structure, agent = behavior).
- Dynamic hiring / org changes at runtime.

## Imports

Use `coactra.organization.repository` for persistence contracts and backends. The older
`coactra.organization.store` and `coactra.organization.sqlite_store` module paths remain
as deprecated compatibility imports for existing callers.

## Production storage

`AsyncPostgresOrgStore` exposes the tenant-checked SQL repository as async methods backed
by PostgreSQL, keeping blocking SQL calls off the event loop. Install
`coactra-organization[postgres]`. `TenantOrgStoreRouter` selects a distinct physical
store per tenant when silo isolation is required.

Authorization is a separate async seam: `Authorizer.check(AuthorizationRequest)` returns
an auditable decision for subject/action/resource checks. `InMemoryAuthorizer` is the
offline default, and `OpenFGAAuthorizer` maps the same request to the official OpenFGA
Python SDK when `coactra-organization[openfga]` is installed.

The domain round trip now includes reporting edges, escalation routes, policy references,
ownership domains, seniority, archived principals, and `created_by` / `approved_by` audit
attribution.
