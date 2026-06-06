# Coactra — Build Handoff & Verification (alpha)

**Date:** 2026-06-06  **Branch:** `feat/agent-core` (unpushed)  **For:** Codex / next contributor — verify what's done, pick up what's left.

This is the state after building the **Agent / Team / Workflow** alpha against the design specs in `design/2026-06-06-*.md`. Keys are internal/rotating — don't treat the opencode key as a secret to protect.

## What was built (all on `feat/agent-core`, committed, not pushed)

Public surface — `from coactra import Agent, Team, Workflow, step, Skill, oidc, StaticToken, serve_agent`:

- **Agent** (`coactra/src/coactra/agent/`, flattened — no more `.sdk`): `Agent.create(model=, name=, tenant=, gateway=, auth=, tools=, memory=, workspace=, skills=, peers=, instructions=, output=)`, `run`/`send`/`stream`, `agent.card`, `agent.serve()`.
  - model by id → `LiteLLMModel` (litellm + coactra.ai thinking-model handling).
  - `gateway=`+`auth=` → token-sliced MCP tools via `MCPToolset(auth=BearerAuth(TokenSource))`. `oidc()` (client-credentials fetch+refresh) / `StaticToken`.
  - `memory=` → auto recall+remember connector over graphiti/mem0 (`memory.py`, guarded).
  - `workspace=` → file tools, `run` allow-listed (`workspace_tools.py`).
  - `skills=` → `Skill(id, description, tags, scopes)` → curated A2A **Agent Card** (`skills.py`).
  - `peers=` → in-process A2A delegation tools (`peers.py`, same-tenant gated).
  - `serve_agent()` / `agent.serve()` → expose via the a2a adapters (`serve.py`).
- **Team** (`team.py`, `matcher.py`): registry + capability matcher (keyword default, `match="semantic"` via ai embeddings) + same-tenant policy + roster.
- **Workflow** (`workflow.py`): data-core `Playbook`/`Step`/`step()`/YAML; `run`/`resume` over a Team (capability routing, **approval pause/resume**, run ledger); `run_goal(goal, team, store=, client=)` triage (reuse promoted / plan via `planner.py` → **candidate**); durable `checkpoint=`/`resume_from` (`checkpoint.py`); candidate store (`playbook_store.py`).
- **Cut:** old ports-`Agent`/`make_agent`/mounting/sync-collaboration/`AIPort`+fakes + the 4 shim packages (−2,494 lines). **Kept** (homelab consumes): `coactra.ai`, async collaboration, a2a adapters, `KeycloakExchanger`, `coactra.workspace`, `coactra.jobs`, `coactra.directory`.
- **Docs:** mkdocs rewritten to this model (`mkdocs build --strict` passes).

## How to verify
1. `cd coactra && ../.venv/bin/python -m pytest -q` → **609 passed, 13 skipped**.
2. `../.venv/bin/python -m ruff check src` → clean.
3. `.venv/bin/python -m mkdocs build --strict` → builds (needs `pip install mkdocs-material`).
4. **Live acceptance** (the real proof): `coactra/tests/agent/test_acceptance_live.py` — **UNTRACKED on purpose** (delete before upload; needs the internal opencode key). Run: `OC_KEY=<key> ../.venv/bin/python -m pytest tests/agent/test_acceptance_live.py -q`. It runs a real Team (`security-agent` + `sre-agent`) through a Workflow against opencode-zen and asserts: capability routing (step→correct specialist), approval pause→resume, durable checkpoint→`resume_from`, `run_goal` triage with the **real planner**, and peer delegation. Standalone script equivalent: `/tmp/coactra_acceptance.py`. **It passed** (`ACCEPTANCE_PASSED`).

## Findings / known gaps (pick-up list)
- **`run_goal` planner credentials:** the planner builds a default `ai.Client` with no `api_base`/`api_key` — pass `client=Client(model=, api_base=, api_key=)` or it fails with "missing credentials." TODO: auto-derive the planner client from the team's agents' model config.
- **Durable = checkpoint-store seam** (persist ledger + `resume_from`), NOT the LangGraph/Temporal engine connector. Those are swappable backends to add later.
- **`peers=` is in-process only.** Remote A2A delegation over `OfficialA2ATransport` is a documented future variant (not built).
- **Semantic matcher** (`match="semantic"`) is wired but only keyword is live-tested.
- **Docs:** Workflow/Team examples are badged "designed"; some maintainer pages link to the specs via GitHub URLs (resolve after push).
- **Renames deferred:** `coactra.jobs`→`coactra.workflow`, `coactra.directory`→`coactra.team` would break homelab (it imports those) — they ride with the **homelab sync** pass (`design/2026-06-06-rename-migration.md`), confirm-first.

## Next / roadmap
1. planner credential auto-derive; durable LangGraph/Temporal backend; remote A2A delegation + serving deployment.
2. homelab sync (the renames) + migrate homelab off the cut layer.
3. **Fleet growth / per-agent "Hermes" (north-star — see below).**

## North-star: a self-growing agent fleet ("Hermes" per agent)
The maintainer wants the fleet to **grow organically** — when they or an end-user adds an agent, it should join the fleet and become reachable/usable without manual wiring. The foundations exist: every Agent has an **identity** (`name`/`tenant`) + a curated **Agent Card** (`skills=`) + an **A2A messenger** (`peers=` out, `serve_agent` in). The path to the vision:
- a **fleet registry** where agents register their card + endpoint on startup (discovery), so a `Team` can be assembled (and grown) from registered agents instead of a static list;
- **remote A2A** so a Team/Workflow can route to agents on other hosts (the "Hermes" messenger per agent — each agent independently reachable + discoverable);
- dynamic capability routing over the live roster (`needs=` → whoever is registered with the skill), so adding a specialist instantly makes it available to every Workflow.
Net: `Agent` (identity+card+messenger) + `Team` (registry/policy) + `Workflow` (routing) already model a fleet; the work is making registration + remote reach + discovery dynamic so the fleet scales with its users.
