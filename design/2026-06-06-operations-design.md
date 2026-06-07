# Coactra Operations — Observability & Error Handling (alpha)

**Date:** 2026-06-06  **Status:** approved direction, pre-implementation. Cross-cutting across Agent / Workflow / Team.

## Observability & tracing

**Standard: OpenTelemetry (GenAI semantic conventions).** coactra **emits** spans/events; it never runs a backend or invents a format.

- **Trace tree.** A run is a root span; child spans for each model call, tool call, memory recall, and A2A delegation. The SDK already yields typed events (`Assistant`/`Thinking`/`ToolCall`/`ToolResult`/`Usage`/`Status`) — these map 1:1 onto OTel span events.
- **Workflow.** A `WorkflowRun` is a trace; each `Step` a span; `Approval` pauses are span events; `Checkpoint`s are span links (resume joins the original trace).
- **Correlation.** `run_id` + scope (`tenant`/`agent`/`session`) as span attributes. **A2A propagates W3C `traceparent`** so a delegation to a peer joins one cross-agent trace.
- **Cost/usage.** Token counts (from the `Usage` event) and cost recorded as span attributes.
- **Exporter (pluggable).** OTLP by default; a console exporter for dev. Reuse pydantic-ai's built-in OTel instrumentation where it exists; add coactra-level spans for workflow/team/memory.
- **Privacy (default-safe).** Prompts, tool arguments, and results can carry **PII/secrets** — so default telemetry records **IDs, counts, types, durations, and hashes/references**, never raw content. Raw prompt/IO capture is **opt-in only** (`capture_content=True`), per OTel GenAI guidance and the OWASP MCP risk of secret leakage.
- **Decision:** OpenTelemetry is the *one* tracing standard — no custom tracing layer. coactra is a connector to OTel.

## Error handling

**One taxonomy: `coactra.errors` (already exists, keep it).** `CoactraError` base + `ErrorCode` (`CONFIG`, `VALIDATION`, `PROVIDER`/`ADAPTER`, `EXECUTION`/`RUNTIME`, `TIMEOUT`, `PERMISSION`, `SECURITY`, `MISSING_EXTRA`), each carrying a `retryable` hint + structured `details`.

- **Surfacing.** Errors become a terminal `Status(state="error")` event in the stream **and** `RunResult.failed(error)` — structured, never silent. Raw provider exceptions are mapped to the taxonomy at the adapter boundary, not leaked.
- **Boundary mapping.** litellm/model errors → `AdapterError` (retryable per type); tool errors → `ToolResult(error=…)` (the model can react/retry); auth/scope failures → `PermissionDeniedError` (not retryable); missing backend → `MissingExtraError`; policy/security violations → `SecurityError`, **fail-closed + audited**.
- **Workflow.** A step failure → `RetryPolicy` (bounded, backoff) → on exhaustion **re-plan** (planner) or **escalate** (peer/human via an approval) → recorded in the run ledger. Nothing fails silently into a "done" state.
- **Decision:** errors are typed, retryable-aware, and always surfaced as events; coactra owns the mapping from underlying libs (litellm/langgraph/a2a-sdk) into its taxonomy.

## Out of scope
Running a tracing/metrics backend; a bespoke metrics format; alerting/SLOs (deployment concern).
