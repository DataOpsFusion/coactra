# Implementation Plan — Agent Core (chunk 1)

**Branch:** `feat/agent-core`  **Method:** subagent-driven-development — TDD, repo `.venv`, commit per task, **no Co-Authored-By, no push**.  **Specs:** agent-api · review-refinements · auth · operations.

Surface stays the 3 nouns; build standards-shaped internals. Each task ends green (full suite + `ruff check src`) before the next.

## Tasks (ordered, each independently verifiable)

1. **Top-level door + `output=` alias.**
   - Add `coactra/src/coactra/__init__.py` with a **lazy `__getattr__`** exporting `Agent` (+ `Run`) from `coactra.agent.sdk` — lazy so importing `coactra` doesn't require the `[agent]` extra (pydantic-ai); `from coactra import Agent` works when `[agent]` is installed.
   - Add `output=` as the preferred alias for `output_type=` on `Agent.run`/`Agent.send` (keep `output_type=` working).
   - **Verify:** `from coactra import Agent` works; offline `FunctionModel`/`TestModel` run; `output=` returns the typed object; **full suite green; ruff clean; hatchling build + `twine check` still pass** (PEP-420 namespace → regular package must not break discovery).

2. **Provider config on `create()`.**
   - `Agent.create(model, api_base=None, api_key=None, **defaults)` threads to `LiteLLMModel` so a real OpenAI-compatible endpoint (opencode zen) works through the string-model path.
   - **Verify offline:** kwargs reach `LiteLLMModel` (assert on a captured completion). **Live smoke (main agent, not a subagent):** `Agent.create(model="openai/qwen3.6-plus", api_base="https://opencode.ai/zen/go/v1", api_key=<oc.key>)` → `run("…")` returns non-empty.

3. **`gateway=` + `auth=` — the primary MCP path (tool-slicing consumer).**
   - `Agent.create(gateway=, auth=)`: connect to the MCP gateway with the token, list **token-sliced** tools, register them as agent tools. `oidc(issuer, client_id, client_secret)` token source = client-credentials **fetch + auto-refresh** (reuse `[oauth]`); `token=` static for dev. `name`/`tenant` read from token claims.
   - **Verify:** with a fake gateway + fake token — tools come from the gateway's filtered list; no manual enumeration; static `token=` and `oidc()` both work.

4. **`memory=` connector (automatic, guarded).**
   - Auto-recall on the user message + auto-remember the turn, delegating to the backend (`InProcess`/`graphiti`/`mem0`). Guardrails: scope (tenant/agent/session), max-injected cap, provenance, write-policy, delete/export path.
   - **Verify:** with `InProcess` backend — recall injected before run, remember after; cap + scope enforced; nothing ranked/stored by coactra itself.

5. **`workspace=` tools.**
   - `read_file`/`write_file`/`list_files`/`run` auto-added when `workspace=` set; `run` allow-list gated (OWASP: no secret leakage / injection).
   - **Verify:** model can write/read in the scoped desk; `run` denied unless allow-listed.

6. **`skills=` + Agent Card + `expose`.**
   - `skills=` accepts a string or `Skill(id, description, tags, scopes)`; `expose=True` publishes the A2A Agent Card; peer discovery fetches a peer's card. Never advertise raw tools.
   - **Verify:** card built from skills (curated only); peer fetch returns skills + securitySchemes, no creds.

## Out of this chunk
Team, Workflow, the `jobs→workflow`/`directory→team` renames, OTel wiring — separate plans after Agent core is solid.

## Live validation
The **main agent** runs the live opencode-zen smoke test (key at `/tmp/oc.key`, base `https://opencode.ai/zen/go/v1`) after Task 2 — subagents stay offline (no key).
