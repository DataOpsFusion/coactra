# Roadmap

The implementation roadmap now follows the alpha-breaking Team-first order:
**Team spine → skill-routed workflow → model resolution → broader adapters and
durability**.

**Build order:**

1. **Team spine** — `Team(scope=..., policy=...)`; explicit catalogs for agents, skills, and workflows; `add_agent()` and `run()` as the main assembly/runtime verbs. *(in flight)*
2. **workspace + memory + peers through Team** — runtime agents still expose file tools, memory bindings, MCP gateway tools, and outbound delegation, but Team owns the construction path.
3. **Workflow** — `Workflow(steps=[...])` + `step()` using `requires_skill`; Team routes steps through `match_skill()` and policy gates.
4. **Model resolution** — `ModelResolver` selects governed model routes; LiteLLM stays an adapter, not Coactra's identity.
5. **Durability and external policy** — LangGraph/Temporal/OpenFGA remain adapters layered under the same execution model.

**What is built today:**

- `run / send().stream()`
- `agent.card` (curated discovery metadata)
- `Team(scope=..., policy=...)` with explicit catalogs and `add_agent(...)`
- `peers=` with local Agent objects, string placeholders, and `RemotePeer(...)`
- `Workflow` / `step()` / `Workflow.run_goal()` with approval pause/resume and checkpoint-store resume
- `requires_skill`-based workflow routing
- `ModelProfile` / `ModelRoute` / `ModelResolver` as the governed model seam
- Outbound A2A via `coactra.agent.adapters.OfficialA2ATransport`

**Delegated to host / external libraries:**

- pydantic-ai `Model` instances and provider strings, plus eventual LiteLLM-backed route execution
- OAuth client-credentials fetch/refresh (`authlib`, `httpx-oauth`)
- Inbound A2A Starlette apps (`a2a-sdk` server APIs)

**Still directional:**

- Fleet registry/discovery for remote A2A endpoints
- OpenFGA/AuthZEN policy adapters
- Automatic learning loop around reflection, promotion, replay, and advertisement

The authoritative source for the phased plan, milestone gates, and implementation
details is the implementation plan spec:

**[design/2026-06-09-team-first-alpha-work-orders.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-09-team-first-alpha-work-orders.md)**

The system vision that sets the Team-first target:

**[design/2026-06-06-coactra-vision.md](https://github.com/DataOpsFusion/coactra/blob/main/design/2026-06-06-coactra-vision.md)**
