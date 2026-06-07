# Coactra

Coactra is an alpha Python library for people who already have models, tools, MCP servers, memory stores, workflow engines, and agent adapters, but want a small composition layer to steer them together.

The preferred application surface is intentionally small:

```python
from coactra import Agent, Skill, Team, Workflow, mcp, step
```

Use lower-level modules only when wiring a backend adapter, persistence store, event stream, or host runtime.

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
agent = await Agent.create(
    model="anthropic/claude-haiku-4-5",
    tools=[mcp("https://gateway.example.com/mcp", name="gateway")],
)
```

## Compose Agents When You Need Routing

```python
security = await Agent.create(name="security", skills=[Skill("cert.rotate")], model=model)
sre = await Agent.create(name="sre", skills=[Skill("deploy")], model=model)
team = Team([security, sre])
```

## Add Workflow Only When The Task Has Shape

```python
workflow = Workflow("release", steps=[
    step("Run checks", needs="test"),
    step("Approve deployment", needs="deploy", approve=True),
])
```

## Development

```bash
make test
make release-check
```

`make release-check` runs lint, compile, tests, docs, examples, clean wheel install validation, live-backend inventory, and whitespace checks.

## Documentation

- [API index](docs/API_INDEX.md): current import contract.
- [Quickstart](docs/getting-started/quickstart.md): Agent-first app flow.
- [Examples](docs/examples/index.md): runnable examples and projects.
- [Production guide](docs/operations/production.md): deployment posture and backend seams.
- [Alpha release checklist](docs/maintainers/alpha-release-checklist.md): release gates.

## Maturity

Coactra is alpha. Breaking import moves are allowed before publishing stable releases, but the current contract is tested: removed alpha roots stay removed, and application code should start from the root package.
