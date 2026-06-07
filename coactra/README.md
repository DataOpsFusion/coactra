# coactra

Single-distribution package for composing existing AI application pieces: Agent, Team, Workflow, MCP toolsets, memory, workspace, and optional backend adapters.

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
from coactra import Agent, Skill, Team, Workflow, mcp, step
```

Use this root surface for application code. Use lower-level modules only for adapters and host runtime wiring:

- `coactra.agent` for event/runtime types and A2A adapter helpers
- `coactra.workflow` and `coactra.workflow.ledger` for workflow engines and durable work storage
- `coactra.team.directory` for org/member/seat persistence
- `coactra.memory` and `coactra.workspace` for backend integration

## Bring Existing Pieces

```python
import asyncio
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from coactra import Agent, mcp


def existing_model(messages, info):
    return ModelResponse(parts=[TextPart("existing model handled it")])


async def main() -> None:
    agent = await Agent.create(
        model=FunctionModel(existing_model),
        tools=[mcp("https://tools.example/mcp", name="tools")],
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
