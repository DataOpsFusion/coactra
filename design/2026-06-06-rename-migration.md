# Coactra Rename & Migration Mechanics (alpha)

**Date:** 2026-06-06  **Status:** approved direction. Alpha (`0.0.x`, effectively unpublished) → rename freely, **no deprecated shims kept**. The only consumer is homelab-mcp, handled in a separate sync pass.

## Target names

| From (today) | To | Public | Internal |
|---|---|---|---|
| `coactra.jobs` (= `work` + `workflow`) + `orchestration` shim | `coactra.workflow` | `Workflow`, `step` | `Playbook`, `WorkflowRun`, `Step`, `Approval`, `Checkpoint` |
| `coactra.directory` + `organization` shim | `coactra.team` | `Team` | registry/roster + policy |
| `coactra.agent.sdk.Agent` | re-exported `coactra.Agent` | `Agent`, `mcp` | — |
| `coactra.ai` | unchanged (internal engine) | — | (optional later → `coactra.models`/`llm` behind a compat alias) |

**Cut (no consumer):** `make_agent`, ports-`Agent`, `mounting.py`/`begin_turn`, sync collaboration, `AIPort`/`FakeAI`.

## Mechanics (order — each its own mechanical commit)

1. **Top-level door.** Add `coactra/__init__.py` exporting `Agent`, `Team`, `Workflow`, `mcp`, `step`. (Converts the PEP-420 namespace package to a regular package — safe now that it's a single distribution.)
2. **`git mv`** the packages (preserve history): `jobs`→`workflow`, `directory`→`team`. Update internal imports (`rg` + `sed`), extras names in `pyproject.toml`, and tests.
3. **Drop the shim packages** (`orchestration`/`organization`/`work`) — alpha, no back-compat.
4. **Verify** — full suite green via the repo `.venv`; `ruff check src` clean; `twine check` the built dist.
5. **homelab sync (SEPARATE repo + commit).** Update homelab imports `coactra.jobs.workflow`→`coactra.workflow`, `coactra.directory`→`coactra.team` (`coactra.ai` unchanged); run homelab tests. **Touches the production consumer — confirm with the user before editing homelab.**

## Guardrails
- Renames are **mechanical, isolated commits** — never mixed with behavior changes, so review is trivial.
- Single distribution → renames are internal; one external consumer → one sync pass.
- Keep `coactra.ai` stable (homelab + the planner import it) — any `ai`→`models` rename is deferred and ships behind a compat alias.
