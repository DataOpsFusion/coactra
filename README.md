# Coactra

Coactra is an alpha Python library for people who already have models, tools, MCP servers, memory stores, workflow engines, and agent adapters, but want a small composition layer to steer them together.

The preferred application surface is intentionally small:

```python
from coactra import Agent, Scope, Skill, Team, Workflow
```

Use lower-level modules only when wiring a backend adapter, persistence store, event stream, or host runtime:

```python
from coactra.agent import MCPServer
from coactra.workflow import step
```

## Install

```bash
pip install "coactra[agent]"
```

Add backend extras only when you use that backend:

```bash
pip install "coactra[agent-gateway,oauth]"  # MCP gateway and OAuth
pip install "coactra[graphiti]"
pip install "coactra[mem0]"
pip install "coactra[langgraph]"
pip install "coactra[sql]"
```

## Bring Your Own Model

```python
import asyncio
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from coactra import Agent


def existing_model(messages, info):
    return ModelResponse(parts=[TextPart("handled by my model")])


async def main():
    agent = await Agent.create(model=FunctionModel(existing_model), instructions="Use host policy.")
    print(await agent.run("can I keep my own model?"))
    await agent.aclose()


asyncio.run(main())
```

## Add MCP Tools Without Owning The Gateway

```python
from coactra import Agent
from coactra.agent import MCPServer

agent = await Agent.create(
    model="anthropic:claude-haiku-4-5",
    tools=[MCPServer(url="https://gateway.example.com/mcp", name="gateway")],
)
```

For the primary MCP path, use `gateway=` + `auth=` on `Agent.create()` instead.

## Compose Agents When You Need Routing

```python
security = await Agent.create(name="security", skills=[Skill("cert.rotate")], model=model)
sre = await Agent.create(name="sre", skills=[Skill("deploy")], model=model)
team = Team([security, sre])
```

## Add Workflow Only When The Task Has Shape

```python
from coactra.workflow import step

workflow = Workflow("release", steps=[
    step("Run checks", needs="test"),
    step("Approve deployment", needs="deploy", approve=True),
])
```

## Development

```bash
make test          # non-live default suite
make type          # pyright type gate
make release-check
```

`make release-check` runs lint, compile, the non-live test suite, docs, examples,
clean wheel/sdist install validation, live-backend inventory, and whitespace checks.
Type checking is a separate gate (`make type`) and is also run by CI.

Live backend tests are excluded from the default test run. Use `make live-check`
for the inventory, or set `COACTRA_RUN_LIVE=1` with the required credentials to
execute configured live checks.

## Documentation

- [API index](docs/API_INDEX.md): current import contract.
- [Quickstart](docs/getting-started/quickstart.md): Agent-first app flow.
- [Bring your own stack](docs/getting-started/bring-your-own.md): models, OAuth, A2A.
- [Examples](docs/examples/index.md): runnable examples and projects.
- [Production guide](docs/operations/production.md): deployment posture and backend seams.
- [Alpha release checklist](docs/maintainers/alpha-release-checklist.md): release gates.

## Maturity and API Stability

Coactra is **alpha** (`0.0.x`). Breaking import moves are allowed before stable
releases, but the current contract is tested: removed alpha roots stay removed,
and application code should start from the root package.

| Surface | Tier | Notes |
|---------|------|-------|
| `from coactra import Agent, Team, Workflow, Scope, ...` | Stable (alpha) | Preferred application entry |
| `coactra.agent`, `coactra.workflow` playbooks | Beta | Adapter/runtime seams |
| `coactra.team.directory`, durable ledger internals | Beta / internal | Deep imports may change |

See [release policy](docs/maintainers/release-policy.md) for the full tier table.

## Security

- Local workspace command execution is **disabled by default**.
- Token passthrough is **rejected**; use RFC 8693 exchange adapters.
- Inbound A2A serving is **host-owned** (wire `a2a-sdk` yourself).

Report vulnerabilities via [SECURITY.md](SECURITY.md) — do not file public issues
for undisclosed security problems.

## Support

- [Documentation](https://dataopsfusion.github.io/coactra/)
- [GitHub Issues](https://github.com/DataOpsFusion/coactra/issues) for bugs and features
- [Changelog](CHANGELOG.md) for release notes
