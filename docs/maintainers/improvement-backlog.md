# Improvement Backlog

This backlog tracks implementation gaps and quality improvements for the current
**Agent · Team · Workflow** architecture. The design decisions are finalized in
the `design/2026-06-06-*.md` specs; this page tracks the work still outstanding
against those decisions.

## Current Milestone: Agent Core

Status of built features (0.0.x):

| Feature | Status |
|---|---|
| `Agent.create(model, tools, instructions, output)` | Built |
| `run / send().stream()` | Built |
| `agent.card` | Built |
| `Team` (registry + keyword matcher + same-tenant policy) | Built |
| `memory="inprocess\|mem0\|graphiti"` | Built |
| `workspace=` (file tools) | Built |
| `gateway=` + `auth=StaticToken` / custom `TokenSource` MCP path | Built |
| `skills=[Skill(...)]` structured roster | Built |
| `peers=` outbound A2A delegation (`RemotePeer`, `OfficialA2ATransport`) | Built |

## Outstanding: Agent Core

- Semantic matcher embedding cache (perf)
- Memory guardrails: injection cap, deletion/export (GDPR), write policy
- Workspace `run` allow-list configuration surface
- Documented recipes for BYO pydantic-ai model, OAuth, and inbound A2A serving

## Outstanding: Workflow Layer

- `Workflow(steps=[...])` authored playbook
- `step()` helper + YAML loader
- `Workflow.run_goal()` triage (reuse / plan / candidate)
