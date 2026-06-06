# AI Library Design

`coactra.ai` is the **internal engine** behind the `Agent` door. Users never import
it directly — `Agent` and the Workflow planner use it. It handles model routing via
LiteLLM, thinking-model compatibility (`reasoning_content` fallback, TOOLS→JSON mode),
structured output via Instructor, embeddings, and reasoning capture/replay.

**Key principles:**

- Internal: `from coactra.ai import ...` is not part of the public API
- Thinking-model safe: `structured()` falls back to JSON mode when `tool_choice=required` is rejected; `ask()` surfaces `reasoning_content` when `content` is empty
- Provider normalization: LiteLLM routes any provider-id; Instructor handles structured output
- Reasoning replay: capture traces, gate on quality, replay to avoid re-spending tokens
- Optional rename `ai` → `models` / `llm` is on the roadmap behind a compat alias

The authoritative design — live findings, thinking-model fixes, factory/client
convenience, and the reasoning-replay core — is the vision document and the
agent API spec (internal/cut section):

**[design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md)**

**[design/2026-06-06-agent-api-design.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-agent-api-design.md)**
