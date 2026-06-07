# Design Implementation Status

Last checked: 2026-06-07

This file reconciles the `design/2026-06-06-*` specs with the current repository.

## Implemented

- Agent facade: `Agent.create()`, `run()`, `send()`, `stream()`, `output` / `output_type`, provider config, memory, workspace, gateway/auth, additive `mcp()` tool tags, peers, skills, cards, and `serve()`.
- Auth basics: `oidc()`, `StaticToken`, gateway bearer auth, token-exchange ports, Keycloak adapter, and conformance tests.
- Team facade: top-level `Team`, canonical `coactra.team`, local roster, keyword matching, optional semantic matcher, same-tenant policy, and Agent Card skill matching.
- Workflow facade: authored `Workflow`, `step`, approval pause/resume, checkpoint-store resume, goal triage, candidate playbook store, and durable engine bridge.
- Work ledger: `WorkManager`, in-memory and SQL stores, leases, retries, checkpoints, decisions, artifacts, audit events, and adapter seams.
- Directory model: OU tree, members, seats, grants, overrides, policy refs, SQLite store, async/Postgres wrapper, OpenFGA authorizer seam, and company bootstrap helpers.
- Operations basics: typed stream events, run/workflow tracing hooks, structured errors for common boundaries, root quality Makefile targets, and production docs.
- Rename migration: product vocabulary is Agent / Team / Workflow. Compatibility-only wrapper modules for old import paths have been removed. Work ledger internals now live under `coactra.workflow.ledger`, and directory internals now live under `coactra.team.directory`.

## Partially Implemented

- Durable execution: LangGraph, Temporal, and Prefect seams exist, but production restart behavior still depends on explicit checkpointer/runtime configuration and live integration validation.
- A2A: serving and outbound transports exist, and a process-local fleet registry can resolve named remote peers. Durable/network-backed discovery and self-registration are still future work.
- Observability: spans/events exist in the main paths, but full OTel exporter configuration and cross-adapter trace coverage are not complete.
- Design verification: live acceptance tests exist but are environment-gated, so the normal local test suite does not prove every external backend path.

## Not Implemented

- Durable fleet registry / Hermes-style self-registration and cross-process discovery.
- Automated clean-venv base-install matrix in CI.
- Mandatory live release gate for OpenCode, Graphiti, mem0, A2A, and durable workflow backends.

## Immediate Cleanup Rules

- New examples should import only current public names from `coactra` or documented adapter modules.
- New Team code should import `Team` from `coactra` or `coactra.team`; use `coactra.team.directory` only for lower-level persistence/directory APIs.
- Do not use removed sync collaboration names; use `AsyncPolicyGatedCollaborator`.
- Do not add compatibility modules for removed paths.
- Use this status file for current implementation truth; obsolete migration and handoff notes were removed.
