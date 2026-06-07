# Roadmap

The implementation roadmap follows the build order: **Agent core → workspace →
Team → Workflow**. Each milestone ships independently; the public surface grows
incrementally as each layer is built.

**Build order:**

1. **Agent core** — `from coactra import Agent`; `Agent.create(model, tools, memory, workspace, skills, peers, instructions)`; `run / send().stream()`; `agent.card`; litellm routing + thinking-model handling. *(built)*
2. **workspace** — `Agent.create(workspace=)` surfaces as `read_file`/`write_file`/`list_files`/`run` tools; allow-list gating for `run`.
3. **Team** — `Team([...])` registry; keyword matcher; same-tenant policy; `match="semantic"` via ai embeddings; `peers=` outbound A2A delegation.
4. **Workflow** — `Workflow(steps=[...])` + `step()`; triage (`run_goal`); durable engine (LangGraph default); approval pauses; planner + candidate playbooks.

**What is built today:**

- `Agent.create(model, name, tenant, gateway, auth, tools, memory, workspace, skills, peers, learned, instructions, output)`
- `run / send().stream()`
- `agent.card` and `serve_agent` / `agent.serve()`
- `Team` (registry + keyword matcher + same-tenant policy)
- `peers=` with local Agent objects, string placeholders, and `RemotePeer(...)`
- `Workflow` / `step()` / `Workflow.run_goal()` with approval pause/resume and checkpoint-store resume

**Still directional:**

- Fleet registry/discovery for remote A2A endpoints
- OpenFGA/AuthZEN policy adapters
- Automatic learning loop around reflection, promotion, replay, and advertisement

The authoritative source for the phased plan, milestone gates, and implementation
details is the implementation plan spec:

**[design/2026-06-06-implementation-plan-agent-core.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-implementation-plan-agent-core.md)**

The system vision that sets the three-noun target:

**[design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md)**
