# workspace

> Charter only — captures the problem + vision. Full design comes later.

## The problem it solves

Every run, the agent re-ingests all its context from scratch — "like your first
day you train." There's no persistent place where it does its work and keeps it.

## The vision

A **long-term living space** for each agent: a filesystem + tools/CLI where the agent
works, *lives*, and keeps what it built — plus **lifecycle interventions** so it stays
healthy over time:
- **auto-compact** — keep the space from bloating.
- **a day-note / handoff** — the agent writes down "what to do next" so the next
  session picks up where it left off, instead of starting from zero.
- **a place to drop an assigned workflow** — you put work in the space and the agent
  operates comfortably inside it.

```python
ws = agent.workspace          # the agent's persistent desk
ws.write("notes.md", ...)     # files stay between sessions
ws.run("ls")                  # requires a sandbox backend, or trusted local opt-in
ws.handoff("tomorrow: ...")   # day-note for the next session
ws.rotate_journal(before=cutoff) # archive older YYYY-MM-DD journal entries
```

## Wraps (swappable backends)

Daytona, E2B, OpenHands, Docker, local filesystem.

## Design verdict

**BUILD a thin control layer over persistent sandboxes.** The field is NOT empty —
Daytona (persistent sandboxes + snapshots + lifecycle + MCP), E2B (pause/resume with fs
+ process state), OpenHands (persists conversation + MCP + tools + agent state), Docker
volumes. None package the **agent desk** (files + CLI policy + handoff/day-note +
mounted-capability manifest). Build that above them. Boundary: the `agent` runtime does
the MCP mounting; `organization` owns hierarchy/policy; `workspace` just stores the desk.

## Open design points (later)

- Where does `workspace` (working files) end and `memory` (recalled facts) begin?
- Isolation per agent; cleanup / archival policy.

## Current Layout

```text
backends/    # backend protocol and local filesystem default
desk.py      # scope-bound Workspace facade
policy.py    # desk-local CLI policy
adapters/      # optional sandbox provider adapters
office.py      # optional office profile, STATUS governance, token accounting
integrations/  # optional memory, organization, MCP, and workflow helpers
```

The reusable desk remains dependency-light. Install optional layers only when needed:

```bash
pip install 'coactra-workspace[office]'
pip install 'coactra-workspace[integrations]'
```

`coactra.workspace.office.OfficeWorkspace` adds a configurable office layout without
changing the base facade. Integration modules are imported explicitly so a plain desk
does not eagerly import memory, organization, MCP, or model dependencies.

### Shared memory integration

`coactra.workspace.integrations.mcp.register_recall_tool(...)` keeps the original
single-agent recall behavior by default. A host may bind allowlisted aliases such as
`department` and `company`, and may supply `MemoryAcl` plus an actor to expose an
ACL-checked `publish_memory` tool. Callers cannot construct arbitrary tenant scopes.

The original `backend.py` and `local.py` module paths remain compatibility imports.

## Local Execution Safety

`LocalFilesystemBackend` confines file operations to `<base>/<tenant>/<agent>`, but a
local subprocess is not a filesystem jail. Local `exec()` therefore fails closed by
default. For trusted development only, opt in with `allow_unsafe_local_exec=True` when
calling `open_workspace(...)`, or `allow_unsafe_exec=True` when constructing the backend.
Use a sandbox-backed adapter for mutually untrusted tenants in production.

## Silo routing

Wrap provider backends with `TenantWorkspaceBackendRouter(factory)` when each tenant must
resolve to a different physical sandbox account, root, or cluster.
