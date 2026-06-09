# Coactra

Coactra is an alpha Python orchestration fabric for agentic systems.

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

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team

resolver = ModelResolver([
    ModelRoute(
        capability="triage",
        profile=ModelProfile(
            name="triage",
            model="openai/qwen3.6-plus",
            api_base="https://opencode.ai/zen/go/v1",
            api_key=os.environ["OC_KEY"],
        ),
    )
])


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="support"),
        policy=Policy.permissive(),
        model_resolver=resolver,
    )
    agent = await team.add_agent(
        name="triage-agent",
        model_capability="triage",
        instructions="Use host policy.",
        skills=[Skill("incident.triage", description="triage incidents")],
        expose=True,
    )
    print(await agent.run("Triage nginx 502s on checkout"))
    await agent.aclose()


asyncio.run(main())
```

## Policy-Gated Model Routes

```python
from pydantic_ai.models.test import TestModel

resolver = ModelResolver([
    ModelRoute(
        capability="fast-chat",
        profile=ModelProfile(name="default-fast", model=TestModel()),
    )
])
team = Team(
    scope=Scope(tenant_id="acme", namespace="ops"),
    policy=Policy.permissive(),
    model_resolver=resolver,
)
agent = await team.add_agent(name="planner", model_capability="fast-chat")
```

`model_capability=` is the governed Team-facing path. Configure one or more routes on `ModelResolver`, then register agents against named capabilities.

## Add MCP Tools Without Owning The Gateway

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team
from coactra.agent import MCPServer

team = Team(
    scope=Scope(tenant_id="acme", namespace="tools"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="tool-agent",
            profile=ModelProfile(
                name="tool-agent",
                model="openai/qwen3.6-plus",
                api_base="https://opencode.ai/zen/go/v1",
                api_key=os.environ["OC_KEY"],
            ),
        )
    ]),
)
agent = await team.add_agent(
    name="tool-agent",
    model_capability="tool-agent",
    tools=[MCPServer(url="https://gateway.example.com/mcp", name="gateway")],
)
```

For the primary MCP path, prefer `gateway=` + `auth=` on `team.add_agent(...)`.

## Compose Teams And Workflows

```python
import os

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Skill, Team, Workflow
from coactra.workflow import step

team = Team(
    scope=Scope(tenant_id="acme", namespace="release"),
    policy=Policy.permissive(),
    model_resolver=ModelResolver([
        ModelRoute(
            capability="security",
            profile=ModelProfile(name="security", model="openai/qwen3.6-plus", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
        ),
        ModelRoute(
            capability="deploy",
            profile=ModelProfile(name="deploy", model="openai/qwen3.6-plus", api_base="https://opencode.ai/zen/go/v1", api_key=os.environ["OC_KEY"]),
        ),
    ]),
)
await team.add_agent(name="security", skills=[Skill("cert.rotate")], model_capability="security", expose=True)
await team.add_agent(name="sre", skills=[Skill("deploy")], model_capability="deploy", expose=True)

workflow = Workflow(
    "release",
    steps=[
        step("Run checks", requires_skill="deploy"),
        step("Approve deployment", requires_skill="cert.rotate", approve=True),
    ],
)
run = await team.run(workflow)
```

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

Coactra is **alpha** (`0.0.x`). Breaking import moves are allowed before stable releases. The root `coactra` exports are the intended application-facing contract; deep imports are adapter and runtime seams.

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
