# coactra

Component-based orchestration library for agentic systems. Coactra is Team-first: `Team` owns agent registration, policy, workflow routing, and model resolution, while `Agent` remains a thin runtime shell over pydantic-ai.

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
from coactra import Team, Scope, Policy, Skill, Workflow
```

Submodule helpers when wiring adapters:

```python
from coactra.agent import MCPServer
from coactra.workflow import step
```

Use the root surface for application code. Use lower-level modules only for adapters and host runtime wiring:

- `coactra.agent` for event/runtime types and outbound A2A transport (`coactra.agent.adapters`)
- `coactra.workflow` and `coactra.workflow.ledger` for workflow engines and durable work storage
- `coactra.team.directory` for org/member/seat persistence
- `coactra.memory` and `coactra.workspace` for backend integration

## Bring Existing Pieces

```python
import asyncio
import os

from coactra import Team
from coactra.agent import MCPServer


async def main() -> None:
    team = Team.local(
        tenant_id="local",
        namespace="default",
        capability="existing-stack",
        model="openai/qwen3.6-plus",
        api_base="https://opencode.ai/zen/go/v1",
        api_key=os.environ["OC_KEY"],
    )
    agent = await team.add_agent(
        name="existing-stack-agent",
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
