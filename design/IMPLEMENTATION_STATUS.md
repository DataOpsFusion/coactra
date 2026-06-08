# Design Implementation Status

Last checked: 2026-06-08

This file reconciles the `design/2026-06-06-*` specs with the current repository.

> **Note:** The June 2026 design specs describe the original Agent core plan. The
> refined architecture (2026-06-08) treats `Agent` as a thin pydantic-ai shell;
> `oidc()`, `serve_agent`, and `LiteLLMModel` have been removed from the public
> surface. See `docs/getting-started/bring-your-own.md`.

## Implemented

- Agent facade: thin pydantic-ai shell — `Agent.create()`, `run()`, `send()`, `stream()`, memory, workspace, gateway/auth, additive `mcp()` tool tags, peers, skills, and `agent.card`.
- Auth basics: `StaticToken`, gateway bearer auth, token-exchange ports, Keycloak adapter, and conformance tests.
- Team facade: top-level `Team`, canonical `coactra.team`, local roster, keyword matching, optional semantic matcher, same-tenant policy, and Agent Card skill matching.
- Workflow facade: authored `Workflow`, `step`, approval pause/resume, checkpoint-store resume, goal triage, candidate playbook store, and durable engine bridge.
- Work ledger: `WorkManager`, in-memory and SQL stores, leases, retries, checkpoints, decisions, artifacts, audit events, and adapter seams.
- Directory model: OU tree, members, seats, grants, overrides, policy refs, SQLite store, async/Postgres wrapper, OpenFGA authorizer seam, and company bootstrap helpers.
- Operations basics: typed stream events, run/workflow tracing hooks, structured errors for common boundaries, root quality Makefile targets, and production docs.
- Outbound A2A: `OfficialA2ATransport` + `RemotePeer` + `CollaborationPolicy` deny-before-wire.
- Rename migration: product vocabulary is Agent / Team / Workflow. Compatibility-only wrapper modules for old import paths have been removed. Work ledger internals now live under `coactra.workflow.ledger`, and directory internals now live under `coactra.team.directory`.

## Partially Implemented

- Durable execution: LangGraph, Temporal, and Prefect seams exist, but production restart behavior still depends on explicit checkpointer/runtime configuration and live integration validation.
- A2A: outbound transport and peer delegation exist; inbound serving is host-owned via `a2a-sdk`. Durable/network-backed discovery and self-registration are still future work.
- Observability: spans/events exist in the main paths, but full OTel exporter configuration and cross-adapter trace coverage are not complete.
- Design verification: live acceptance tests exist but are environment-gated, so the normal local test suite does not prove every external backend path.

## Not Implemented

- Durable fleet registry / Hermes-style self-registration and cross-process discovery.
- Automated clean-venv base-install matrix in CI.
- Mandatory live release gate for OpenCode, Graphiti, mem0, A2A, and durable workflow backends.

## Removed from public surface (refined Option B)

- `coactra.oidc()` — use authlib or httpx-oauth; pass `TokenSource` to `auth=`
- `coactra.serve_agent` / `Agent.serve()` — use a2a-sdk server APIs directly
- `coactra.agent.litellm_model.LiteLLMModel` — pass pydantic-ai `Model` or provider string
