# Improvement Backlog

This backlog tracks implementation gaps and quality improvements for the current
policy-aware **Team · Agent · Workflow** composition surface. The design decisions are finalized in
the `design/2026-06-06-*.md` specs; this page tracks the work still outstanding
against those decisions.

## Current Milestone: Team-First Alpha Cut

Status of major features (0.0.x alpha):

| Feature | Status |
|---|---|
| `Team(scope=..., policy=...)` | Built |
| `team.add_agent(...)` | Built |
| `run / send().stream()` | Built |
| `agent.card` | Built |
| `memory="inprocess\|mem0\|graphiti"` | Built |
| `workspace=` (file tools) | Built |
| `gateway=` + `auth=StaticToken` / custom `TokenSource` MCP path | Built |
| `skills=[Skill(...)]` structured roster | Built |
| `peers=` outbound A2A delegation (`RemotePeer`, `OfficialA2ATransport`) | Built |
| broad `requires_skill` routing with `required_tags` fail-closed disambiguation | Built |
| approval proof bundles and `approval_only=True` gates | Built |
| `Workflow.code_change(...)` thin builder | Built |
| `ModelResolver` / `ModelProfile` / `ModelRoute` | Built |

## Outstanding: Team and Agent Layer

- Semantic matcher embedding cache (perf)
- Memory guardrails: injection cap, deletion/export (GDPR), write policy
- Workspace `run` allow-list configuration surface
- More documented production route recipes for OpenCode/Zen, LiteLLM, and host-managed gateways
- Documented recipes for OAuth and inbound A2A serving

## Outstanding: Workflow Layer

- richer workflow-candidate review and promotion UX
- reusable verification profile libraries on top of the typed verifier/check model
- planner support for emitting verifier roles and richer workflow candidates
- broader conformance tests for policy-enforced routing and resume semantics across adapters
- optional bounded retry/rework policies layered above the single-pass code-change helper
