from __future__ import annotations

import asyncio

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import Agent, mcp


def existing_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("mcp toolset attached")])


async def main() -> None:
    agent = await Agent.create(
        model=FunctionModel(existing_model),
        tools=[mcp("https://tools.example/mcp", name="existing-tools")],
    )
    try:
        print("mcp_toolsets=", len(agent._runtime._mcp_toolsets))
    finally:
        await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
