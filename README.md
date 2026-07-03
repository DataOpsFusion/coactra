# Coactra

Coactra is an alpha policy-aware composition library for AI workloads.

It gives you a small set of composable primitives — `Scope`, `Policy`, `Team`, `Agent`, `Skill`, `Workflow`, and `Run` — and lets you wire them to existing model, memory, tool, and workflow ecosystems without making those ecosystems Coactra's identity.

The preferred application surface is intentionally small:

```python
from coactra import (
    Agent,
    Decision,
    DecisionOutcome,
    ModelProfile,
    ModelResolver,
    ModelRoute,
    Policy,
    PolicyRequest,
    Scope,
    Skill,
    StaticToken,
    Team,
    Workflow,
)
```

## Install

```bash
pip install "coactra[agent]"
```

Add backend extras only when you use that backend:

```bash
pip install "coactra[agent-gateway,oauth]"
pip install "coactra[graphiti]"
pip install "coactra[mem0]"
pip install "coactra[langgraph]"
pip install "coactra[sql]"
```

## Team-First Quick Start

```python
import asyncio
import os

from coactra import Skill, Team


async def main() -> None:
    team = Team.local(
        tenant_id="acme",
        namespace="support",
        capability="triage",
        model="openai/deepseek-v4-pro",
        api_base="https://opencode.ai/zen/go/v1",
        api_key=os.environ["OC_KEY"],
    )
    agent = await team.add_agent(
        name="triage-agent",
        instructions="Use host policy.",
        skills=[Skill("incident", description="triage incidents", tags=["triage"])],
        expose=True,
    )
    print(await agent.run("Triage nginx 502s on checkout"))
    await agent.aclose()


asyncio.run(main())
```

## Policy-Gated Model Routes

```python
from coactra import Policy, Scope, Team
from pydantic_ai.models.test import TestModel

team = Team(
    scope=Scope(tenant_id="acme", namespace="ops"),
    policy=Policy.permissive(),
)
team.add_model("fast-chat", TestModel())
agent = await team.add_agent(name="planner", model_capability="fast-chat")
```

`model_capability=` is the governed Team-facing path. Configure named routes with
`team.add_model(...)`, then register agents against those capabilities. The lower
level `ModelResolver`, `ModelRoute`, and `ModelProfile` types remain available
for advanced integrations, but normal application code should not need to
construct them directly.

## Add MCP Tools Without Owning The Gateway

```python
import os

from coactra import Team
from coactra.agent import MCPServer

team = Team.local(
    tenant_id="acme",
    namespace="tools",
    capability="tool-agent",
    model="openai/deepseek-v4-pro",
    api_base="https://opencode.ai/zen/go/v1",
    api_key=os.environ["OC_KEY"],
)
agent = await team.add_agent(
    name="tool-agent",
    tools=[MCPServer(url="https://gateway.example.com/mcp", name="gateway")],
)
```

For the primary MCP path, prefer `gateway=` + `auth=` on `team.add_agent(...)`.

## Compose Teams And Workflows

```python
import os

from coactra import Policy, Scope, Skill, Team, Workflow
from coactra.workflow import step

team = Team(
    scope=Scope(tenant_id="acme", namespace="release"),
    policy=Policy.permissive(),
)
team.add_model(
    "deploy",
    model="openai/deepseek-v4-pro",
    api_base="https://opencode.ai/zen/go/v1",
    api_key=os.environ["OC_KEY"],
)
team.add_model(
    "review",
    model="openai/deepseek-v4-pro",
    api_base="https://opencode.ai/zen/go/v1",
    api_key=os.environ["OC_KEY"],
)
await team.add_agent(
    name="release-sre",
    skills=[Skill("deploy", description="Execute release work", tags=["execute"])],
    model_capability="deploy",
    expose=True,
)
await team.add_agent(
    name="release-review",
    skills=[Skill("deploy", description="Review release evidence", tags=["review"])],
    model_capability="review",
    expose=True,
)

workflow = Workflow(
    "release",
    steps=[
        step("Run checks", requires_skill="deploy", required_tags=["execute"]),
        step("Review release evidence", requires_skill="deploy", required_tags=["review"]),
        step("Approve deployment", approve=True, approval_only=True),
    ],
)
run = await team.run(workflow)
```

Broad skill ids stay reusable; `required_tags` keeps routing deterministic when multiple agents share the same domain. Approved steps resume with a `ProofBundle`, and `Workflow.code_change(...)` provides a thin implement/verify/review helper for common change-management flows.

## Development

```bash
make test
make type
make release-check
```

`make release-check` runs lint, compile, the non-live test suite, docs, examples, clean wheel/sdist install validation, live-backend inventory, and whitespace checks.

## Documentation

- [API index](docs/API_INDEX.md): current import contract.
- [Quickstart](docs/getting-started/quickstart.md): Team-first app flow.
- [Bring your own stack](docs/getting-started/bring-your-own.md): models, OAuth, A2A.
- [Examples](docs/examples/index.md): runnable examples and projects.
- [Production guide](docs/operations/production.md): deployment posture and backend seams.
- [Alpha release checklist](docs/maintainers/alpha-release-checklist.md): release gates.

## Maturity and API Stability

Coactra is **alpha** (`0.x`). Breaking import moves are allowed before stable releases. The root `coactra` exports are the intended application-facing contract; deep imports are adapter and runtime seams.

| Surface | Tier | Notes |
|---------|------|-------|
| `from coactra import Team, Workflow, Scope, Policy, ...` | Stable (alpha) | Preferred application entry |
| Standalone agent factory | Removed | Use `Team.add_agent(...)` instead |
| `coactra.agent`, `coactra.workflow` runtime helpers | Beta | Adapter/runtime seams |
| `coactra.team.directory`, durable ledger internals | Beta / internal | Deep imports may change |

See [release policy](docs/maintainers/release-policy.md) for the full tier table.

## Security

- Local workspace command execution is **disabled by default**.
- Token passthrough is **rejected**; use RFC 8693 exchange adapters.
- Inbound A2A serving is **host-owned**.
- Every governed action should flow through explicit `Policy` + `Scope`.

## Support

- [Documentation](https://dataopsfusion.github.io/coactra/)
- [GitHub Issues](https://github.com/DataOpsFusion/coactra/issues)
- [Changelog](CHANGELOG.md)
