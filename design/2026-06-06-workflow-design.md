# Coactra Workflow — Design (alpha)

**Date:** 2026-06-06  **Status:** approved direction, pre-implementation.  **Depends on:** Agent spec, Team (roster + policy).

## Goal

A **Workflow** is a playbook of steps plus the manager that runs it across the **Team**. It plans or reuses a playbook, assigns each step to an **Agent** (by name or capability), and drives every step to done — durably, with retries and approvals. "Work order / job / orchestration" are *a Workflow running*, not separate things. coactra is the **connector**: it owns the data model + the run orchestration, and delegates durable execution to an engine and planning to `ai`.

## Public surface

```python
from coactra import Workflow
from coactra.workflow import step

# authored playbook (the step() helper just builds the data core)
play = Workflow("rotate-cert", steps=[
    step("rotate the prod cert", needs="cert rotation"),   # routed by capability
    step("redeploy", agent="sre-1", approve=True),         # pinned + needs approval
])
await play.run(team, durable=True)

# or hand it a goal — triage decides reuse vs plan
await Workflow.run_goal("rotate prod cert and redeploy", team=team)
```

A playbook can equally be loaded from YAML/dict — same data core.

## Decisions

1. **Source = triage (built A→B→C).** `run_goal(goal, team)` triages: a **known goal** runs the **saved playbook** (cheap, reliable — safe for dumb worker models); a **new goal** is **planned** (the planner turns the goal into a playbook via `ai`) and run; the planned playbook is saved only as a **candidate**, promoted into the reusable library after review or N successful runs — **never auto-saved** (prevents the library self-poisoning with bad generated playbooks). Built in order: authored playbooks first → planner → candidate/promote triage on top. So authored playbooks are step 1 of triage.

2. **Assignment = name or capability (one resolver).** A step targets an Agent either by **name** (`step("…", agent="security-agent")`) or by **capability** (`step("…", needs="certs")`). One resolver underneath: a name is the trivial match; a capability matches against each Agent's `skills=` roster in the **Team**. Pin what you know, route the rest. Ties need a rule (first match / Team-defined priority).

3. **Resilience = durable, engine as connector.** Execution is delegated to a durable engine (**LangGraph default**; Temporal/Prefect swappable) — coactra does not reimplement durability. A run survives restart and resumes where it left off. **Approvals are a step property** (`approve=True`, or a green/yellow/red tier): the run **pauses durably**, a human decides, the run **resumes** — even hours later, across restarts. Retries are a step/policy property.

4. **Format = one data core, code is sugar.** The canonical playbook is **plain data** (dict/JSON) — what the planner emits, what's saved, what's replayed (triage forces this; you can't store/replay Python objects). `Workflow(...)`/`step(...)` are a **thin typed helper** that builds that data; **YAML loads into the same core**. One core, two front doors, nothing duplicated.

## How it composes

```
goal
 └─ Workflow: triage → reuse saved playbook  OR  plan a new one (planner via ai) → save as CANDIDATE
     └─ for each step: resolve to an Agent (name, or capability via Team roster)
         └─ run on that Agent  (which may delegate to a teammate — A2A, same Team)
     └─ drive to done: durable checkpointing · retry on failure · pause for approval
```

## Connector boundaries (what coactra owns vs delegates)

- **Owns:** the data model (`Playbook`/`Step`), the step→Agent resolver, the triage orchestration, the run wiring, the `step()`/YAML front doors.
- **Delegates:** durable execution → LangGraph/Temporal/Prefect engines; planning (goal→playbook) → `ai.structured`; playbook matching for triage → the playbook store + similarity (reuse `ai` embeddings); persistence of saved playbooks → a pluggable store.
- **Never:** reimplements a workflow engine, a planner model, or a vector store.

## Today vs target

**Today (`coactra.workflow`):** `Procedure`/`Step`, durable engines (LangGraph/Temporal/Prefect), approval interrupts (`WorkflowInterrupt`), trace→procedure induction, capability registry.

**Target (to build):** `run_goal` triage (reuse/plan/save); capability routing via the Team roster; the data-core playbook + `step()` helper + YAML loader; a **Planner** (goal→playbook) over `ai`; a **playbook store + matcher** for triage; completed package move to `coactra.workflow.ledger`.

## Out of scope (this spec)

Richer DSL beyond steps + capability-routing + approval (parallel/loop/branch land later); the Team spec (roster + who-may-talk policy — its own session); migrating homelab off `coactra.workflow`.
