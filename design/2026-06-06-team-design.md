# Coactra Team — Design (alpha)

**Date:** 2026-06-06  **Status:** approved direction, pre-implementation.  **Used by:** Agent (peers/policy), Workflow (capability routing).

## Goal

A **Team** is "a bag of Agents + policy" — the roster a Workflow routes steps over, and the who-may-talk policy for A2A. It is **optional**: a solo Agent needs no Team. Compose one when you want capability-routing, shared policy, or hierarchy.

## Public surface

```python
from coactra import Team

team = Team([sre, security, network])                       # keyword matching (default)
team = Team([sre, security, network], match="semantic",     # opt into embedding match
            manager="sre-1")                                # optional hierarchy

await Workflow.run_goal("rotate prod cert…", team=team)     # Workflow routes over the Team
```

## Decisions

1. **Assembly = optional & composable.** Single agent → no Team. `Team([...])` groups agents for routing/policy/hierarchy; the two paths nest cleanly. (Mix-and-match.)

2. **Matching = one matcher seam.** A step's `needs=` resolves against each agent's `skills=` roster through a swappable matcher: **keyword/tag by default** (deterministic, no model, debuggable), `match="semantic"` opts into embedding similarity (reuses `ai` embeddings — connector, no new dependency). A pinned `step("name", …)` is the trivial match. Ties: first match, or a Team-defined priority.

3. **who-may-talk = same-tenant by default.** An Agent may talk to peers in the same `tenant`; configurable with a custom policy. From the discovery decision: **seeing ≠ calling** — the curated `skills=` roster is discoverable (same-tenant), but every delegation is still auth-gated (token exchange + policy). Raw tools are never advertised.

4. **Hierarchy/escalation = optional.** A Team may name a `manager` / reporting chain for escalation; not required for alpha. Maps onto the existing org-tree pieces when richer structure is needed.

## The capability roster

Each Agent's author-written `skills=` blurb is its roster entry; the Team aggregates them for matching (decision 2) and discovery (decision 3). Curated strings only — never tool names/args.

## How it composes

Workflow routes each `needs=` step to a Team member via the matcher; A2A peer calls are gated by the Team's policy. The Team is the single place "who exists + who-may-talk + who-can-do-what" lives.

## Connector boundaries

- **Owns:** the Team registry (agents + skills + policy), the matcher seam (keyword default), policy evaluation.
- **Delegates:** semantic matching → `ai` embeddings; richer org structure/permissions (inheritance, seats, external authz) → the existing directory backends (sqlite/postgres/openfga) only when needed.
- **Never:** reimplements an authorization engine or an embedding store.

## Today vs target

**Today (`coactra.directory` + `coactra.agent.collaboration`):** `Organization` tree, `Authorizer` (in-memory/OpenFGA), `OrgStore`, `AllowSameTenant` policy, `AgentRef`.

**Target:** a `Team` facade (bag of agents + `match` + policy) over those pieces; the keyword matcher; the optional semantic matcher via `ai`; rename `coactra.directory`/`organization` → `coactra.team`.

## Out of scope (this spec)

Deep org-tree/permission modeling (inheritance, seats) — stays in directory backends, surfaced only as needed; migrating homelab off `coactra.directory`.
