# Design Implementation Status

Last checked: 2026-06-09

This file reconciles the current design notes with the repository state.

> **Note:** The current alpha surface is Team-first: `Team` owns assembly and routing,
> `Agent` is a runtime type, `requires_skill` replaces free-text workflow needs,
> and governed model selection now flows through `Policy` plus `ModelResolver`.

## Implemented

- Team-first facade: explicit `Team(scope=..., policy=...)`, Team-owned agent/skill/workflow catalogs, `add_agent()`, `add_workflow()`, `match_skill()`, and `run()`.
- Agent runtime: thin pydantic-ai shell with `run()`, `send()`, `stream()`, memory, workspace, gateway/auth, additive `mcp()` tool tags, peers, learned procedures, and `agent.card`.
- Policy seam: shared `Policy`, `PolicyRequest`, and `Decision` contracts; workspace, memory, and collaboration adapters delegate into the same decision model.
- Model routing: `ModelProfile`, `ModelRoute`, and `ModelResolver` provide governed route selection; raw pydantic-ai `model=` remains a temporary escape hatch.
- Workflow facade: authored `Workflow`, `step`, `requires_skill`, approval pause/resume, checkpoint-store resume, goal triage, candidate playbook store, and durable engine bridge.
- Work ledger: `WorkManager`, in-memory and SQL stores, leases, retries, checkpoints, decisions, artifacts, audit events, and adapter seams.
- Directory model: OU tree, members, seats, grants, overrides, policy refs, SQLite store, async/Postgres wrapper, OpenFGA authorizer seam, and company bootstrap helpers.
- Operations basics: typed stream events, run/workflow tracing hooks, structured errors for common boundaries, root quality Makefile targets, and production docs.
- Outbound A2A: `OfficialA2ATransport` + `RemotePeer` + collaboration policy deny-before-wire.
- Alpha cleanup: the standalone agent factory was removed from implementation, `coactra.team` was reduced to `Team`, and current docs/examples were rewritten to Team-first construction.

## Partially Implemented

- Durable execution: LangGraph, Temporal, and Prefect seams exist, but production restart behavior still depends on explicit checkpointer/runtime configuration and live integration validation.
- A2A: outbound transport and peer delegation exist; inbound serving is host-owned via `a2a-sdk`. Durable/network-backed discovery and self-registration are still future work.
- Observability: spans/events exist in the main paths, but full OTel exporter configuration and cross-adapter trace coverage are not complete.
- Design verification: live acceptance tests exist but are environment-gated, so the normal local test suite does not prove every external backend path.
- Model routing rollout: the policy-governed resolver seam exists, but a full LiteLLM-backed adapter path is still an adapter-layer follow-up rather than a completed runtime default.

## Not Implemented

- Durable fleet registry / Hermes-style self-registration and cross-process discovery.
- Automated clean-venv base-install matrix in CI.
- Mandatory live release gate for OpenCode, Graphiti, mem0, A2A, and durable workflow backends.

## Removed from public surface

- standalone agent factory — use `Team.add_agent(...)`
- hidden permissionless Team defaults — pass explicit `policy=`
- free-text workflow requirements — use `requires_skill=`
- `coactra.oidc()` — use authlib or httpx-oauth; pass `TokenSource` to `auth=`
- `coactra.serve_agent` / `Agent.serve()` — use a2a-sdk server APIs directly
- `coactra.agent.litellm_model.LiteLLMModel` — pass pydantic-ai `Model` or provider string
