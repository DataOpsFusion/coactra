# Library Map

One `pip install`-able distribution (`coactra`) with capability modules selected via extras.
Each module has one job and a clean public interface.

!!! info "Legend"
    - **Available (0.0.x)** — implemented and usable today.
    - **Designed / coming** — fully specified in `design/`; not yet shipped.

## Public names

| Name | Import | Role | Status |
|------|--------|------|--------|
| `Agent` | `from coactra import Agent` | The single entry point. Creates an agent, runs prompts, streams events. | **Available** |
| `Skill` | `from coactra import Skill` | A structured skill entry for the Agent Card (`id`, `description`, `tags`, `scopes`). | **Available** |
| `oidc` | `from coactra import oidc` | OAuth 2.1 client-credentials token source (fetch + auto-refresh). | **Available** |
| `StaticToken` | `from coactra import StaticToken` | A pre-fetched JWT token source for development / CI. | **Available** |
| `mcp` | `from coactra import mcp` | Tag an extra MCP server URL (`tools=[mcp("url")]`). Additive to the gateway. | **Available** |
| `Team` | `from coactra import Team` | Roster of Agents with capability matching and who-may-talk policy. | **Designed / coming** |
| `Workflow` | `from coactra import Workflow` | Playbook runner: plans, assigns steps to Agents, drives durably to done. | **Designed / coming** |
| `step` | `from coactra import step` | Helper that builds a Workflow step (name, agent or needs, approve). | **Designed / coming** |

## Internal modules (not imported by users)

| Module | Role | Status |
|--------|------|--------|
| `coactra.ai` | Internal engine: litellm routing, thinking-model handling, embeddings, structured output. `Agent` and the Workflow planner use it; users never import it. | **Available** |
| `coactra.agent.sdk` | The Agent facade + runtime + event types. The implementation behind `Agent.create`. | **Available** |
| `coactra.memory` | Memory backend connector. Backend-neutral `recall`/`remember`; `memory="graphiti"` wires graphiti. | **Available** |
| `coactra.workspace` | Workspace capability. Surfaces a file desk as agent tools (`read_file`, `write_file`, `list_files`, `run`). | **Available** |
| `coactra.directory` | Directory/registry: tenant org tree, permissions, escalation, authorization seams. Becomes `coactra.team` after the Team rename. | **Available** (pre-rename) |
| `coactra.jobs` | Durable work-order ledger and procedure engine adapters. Becomes `coactra.workflow` after the Workflow rename. | **Available** (pre-rename) |

## Installation extras

```bash
pip install coactra                        # base (dependency-light core)
pip install "coactra[agent]"              # Agent runtime (pydantic-ai + litellm)
pip install "coactra[agent-gateway]"      # + OAuth 2.1 client for gateway+auth
pip install "coactra[graphiti]"           # + graphiti memory backend
pip install "coactra[langgraph]"          # + LangGraph durable workflow engine
pip install "coactra[all]"               # everything
pip install "coactra[all,dev]"           # + test/lint tooling
```

## Dependency shape

```
coactra.ai                         (internal engine — foundation)
    |
    +-- coactra.memory             (memory backend connector)
    +-- coactra.workspace          (file desk + workspace tools)
    +-- coactra.directory          (registry, policy, org tree)
    +-- coactra.jobs               (work-order ledger, procedure engine)
    |
    +-- coactra.agent              (wires everything; the Agent facade lives here)
```

`memory`, `workspace`, `directory`, and `jobs` are independent capability modules — none
depends on the other's core. Only `coactra.agent` depends on everything. No circular
dependencies.

## Design philosophy

- **Thin orchestration, not re-implementation.** Each module is a connector over best-of-breed
  libraries. Wire them cleverly; never reimplement what a dependency already does.
- **Named capabilities, not built objects.** `model="claude-sonnet-4-5"`, `memory="graphiti"`,
  `workspace="./desk"` — name the thing, don't construct it.
- **Flexibility at the seams, not the core.** One working default, a clean Protocol interface,
  swappable backends.
- **Security is first-class.** Tool poisoning, secret leakage, scope creep, and command injection
  are explicit design concerns across tools, MCP, and workspace — not afterthoughts.

## Compatibility note

The modules `coactra.directory` and `coactra.jobs` will be renamed to `coactra.team` and
`coactra.workflow` in a future alpha release. The old import names `coactra.work`,
`coactra.orchestration`, and `coactra.organization` are compatibility shims that will be
removed without a deprecation window (alpha has no back-compat guarantee). See
[Naming Migration](naming-migration.md) for details.
