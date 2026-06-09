# Coactra Team Design

**Status:** current Team-first alpha contract.

## Goal

`Team` is the assembly and coordination root. It owns the authoritative scope,
policy, agent registry, skill catalog, workflow catalog, and routing behavior
for a Coactra application.

## Public shape

```python
from coactra import Policy, Scope, Team, Workflow

team = Team(
    scope=Scope(tenant_id="acme", namespace="ops"),
    policy=Policy.permissive(),
)

await team.add_agent(name="security", model_capability="reasoning")
team.add_skill(...)
team.add_workflow(Workflow("rotate-cert", steps=[...]))
await team.run("rotate-cert")
```

## Decisions

1. **Team is the public assembly door.**
   - `scope` is explicit
   - `policy` is explicit
   - permissive behavior must be chosen deliberately

2. **Team owns the canonical catalogs.**
   - agents
   - skills
   - workflows
   - model-routing defaults

3. **Capability routing is exact by default.**
   - workflow steps use `requires_skill=`
   - Team routes through `match_skill(skill_id)`
   - `agent=` remains an override when a step must be pinned

4. **Collaboration is policy-gated.**
   - Team policy is the canonical collaboration authority
   - local or remote peer calls are denied before the wire when not allowed

5. **Team stays lean.**
   - richer org/directory/control-plane concepts remain deeper seams
   - Team is powerful enough to represent an org node
   - Team is not required to model a whole enterprise hierarchy publicly

## Ownership

- Team defines and assigns.
- Agent acts.
- Workflow defines process.
- Policy governs execution.
- Scope locates execution.

## Connector boundaries

- Coactra owns Team catalogs, routing, and Team-level policy wiring.
- Directory stores, OpenFGA adapters, and richer org topology remain advanced seams.
- Team does not own low-level workflow runtime engines or memory storage engines.
