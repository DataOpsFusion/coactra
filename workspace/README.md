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
ws.run("ls")                  # tools/cli, scoped to the desk
ws.handoff("tomorrow: ...")   # day-note for the next session
```

## Wraps (swappable backends)

Daytona, E2B, OpenHands, Docker, local filesystem.

## Verdict (from research — see ../RESEARCH-VERDICTS.md)

**BUILD a thin control layer over persistent sandboxes.** The field is NOT empty —
Daytona (persistent sandboxes + snapshots + lifecycle + MCP), E2B (pause/resume with fs
+ process state), OpenHands (persists conversation + MCP + tools + agent state), Docker
volumes. None package the **agent desk** (files + CLI policy + handoff/day-note +
mounted-capability manifest). Build that above them. Boundary: the `agent` runtime does
the MCP mounting; `organization` owns hierarchy/policy; `workspace` just stores the desk.

## Open design points (later)

- Where does `workspace` (working files) end and `memory` (recalled facts) begin?
- Isolation per agent; cleanup / archival policy.
