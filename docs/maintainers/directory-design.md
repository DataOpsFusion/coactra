# Team Design

The old `coactra.directory` / `coactra.organization` package is being renamed and
redesigned as `coactra.team`. A **Team** is a lean agent registry: a bag of agents
plus a capability matcher and a who-may-talk policy. It is the roster a Workflow
routes steps over, and the policy gate for A2A peer calls.

**Key principles:**

- `Team([agent_a, agent_b])` — bag of agents; optional `match=` and `manager=`
- Capability matching resolves `step(needs=...)` against each agent's `skills=` roster
- Default policy: same-tenant agents may talk; cross-tenant is denied before the wire
- Keyword/tag matching is the default (deterministic, no model); `match="semantic"` opts into embeddings
- Hierarchy and escalation are optional add-ons, not the core abstraction

The authoritative spec — matcher decisions, policy seam, discovery model, and the
target rename from `directory` → `team` — is the team design document:

**[design/2026-06-06-team-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-team-design.md)**

The review refinements clarify that Team stays a lean registry, not an org-chart
simulation:

**[design/2026-06-06-review-refinements.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-review-refinements.md)**
