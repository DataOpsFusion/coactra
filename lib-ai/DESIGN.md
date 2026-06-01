# fleetlib.ai — v0.2 (thinking-model-safe)

> Live testing against opencode zen (2026-06) proved two real gaps: the wrap shelf breaks
> on "thinking"/reasoning models (which is the user's whole fleet — qwen3.6-plus,
> kimi-k2.6, minimax-m3). v0.2 fixes those + a small provider-config convenience. Keep the
> reasoning-replay core (it already passed) and the Protocol/DI design.

## Live findings to fix
1. **`structured()` fails on thinking models.** instructor's default TOOLS mode sends
   `tool_choice=required`, which the provider rejects: *"tool_choice ... not supported in
   thinking mode"*. FIX: use instructor **JSON mode** (`Mode.JSON`) for these models —
   either as the default, or auto-detected/configurable with a clean fallback (try TOOLS,
   fall back to JSON on the tool_choice error). Must round-trip a typed model on
   qwen3.6-plus live.
2. **`ask()` returns empty on thinking models.** Output lands in the message's
   `reasoning_content` (or `reasoning`) field, not `content`, so `ask()` returns `""`.
   FIX: when `content` is empty/None, surface `reasoning_content`/`reasoning` if present
   (and document it). Optionally expose a `think()` that returns both. Must return
   non-empty for minimax-m3 / deepseek-v4-flash live.

## Light cleanup (clean-interface principle)
- A small **factory/config convenience** so callers point at a provider without repeating
  base_url/key/model on every call: e.g. `make_completer(model=, api_base=, api_key=)` →
  a `Completer` you inject into `ReasoningEngine`/`structured`, OR a `Client(model=,
  api_base=, api_key=)` facade with `.ask/.structured`. Keep `ask/structured` standalone
  too. DI preserved (Completer/EmbeddingFn/ReasoningStore Protocols stay injectable).
- Do NOT break the existing 32-test reasoning-replay core or its guardrails.

## Tests
- Unit: structured() JSON-mode path + the tool→json fallback (mocked); ask() reasoning_content
  fallback (mocked); the new factory/client. Keep the 32 existing tests green.
- LIVE (env-gated, skip if no key at /tmp/oc.key or OC_KEY unset): structured() returns a
  valid typed object from qwen3.6-plus; ask() returns non-empty from a thinking model.
  Base url https://opencode.ai/zen/go/v1, models qwen3.6-plus / minimax-m3 / kimi-k2.6.
- Never fake green; report real numbers incl. live pass/skip.
