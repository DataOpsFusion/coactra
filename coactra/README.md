# coactra

Composition and persistence library for multi-agent workflows. `Agent` is a thin shell over pydantic-ai; `Team`, `Workflow`, and `WorkManager` are the core. Bring your own pydantic-ai `Model`, OAuth token source, and inbound A2A server (via a2a-sdk).

```bash
pip install "coactra[agent]"
```

Common extras:

```bash
pip install "coactra[agent-gateway,oauth]"  # MCP gateway and OAuth
pip install "coactra[graphiti]"
pip install "coactra[mem0]"
pip install "coactra[langgraph]"
pip install "coactra[sql]"
```

## Small Surface

```python
from coactra import Agent, Scope, Skill, Team, Workflow
```

Submodule helpers when wiring adapters:

```python
from coactra.agent import MCPServer
from coactra.workflow import step
```

Use this root surface for application code. Use lower-level modules only for adapters and host runtime wiring:

- `coactra.agent` for event/runtime types and outbound A2A transport (`coactra.agent.adapters`)
- `coactra.workflow` and `coactra.workflow.ledger` for workflow engines and durable work storage
- `coactra.team.directory` for org/member/seat persistence
- `coactra.memory` and `coactra.workspace` for backend integration

## Bring Existing Pieces

```python
import asyncio
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from coactra import Agent
from coactra.agent import MCPServer


def existing_model(messages, info):
    return ModelResponse(parts=[TextPart("existing model handled it")])


async def main() -> None:
    agent = await Agent.create(
        model=FunctionModel(existing_model),
        tools=[MCPServer(url="https://tools.example/mcp", name="tools")],
        memory="inprocess",
        workspace="./desk",
    )
    try:
        print(await agent.run("Use my existing stack"))
    finally:
        await agent.aclose()


asyncio.run(main())
```

See `examples/acceptance/` for the checked examples that define the alpha acceptance path.
