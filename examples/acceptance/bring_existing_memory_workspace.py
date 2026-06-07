from __future__ import annotations

import asyncio
import tempfile

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import Agent


def existing_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("memory and workspace stayed external")])


async def main() -> None:
    with tempfile.TemporaryDirectory() as desk:
        agent = await Agent.create(
            model=FunctionModel(existing_model),
            memory="inprocess",
            workspace=desk,
            name="support-agent",
            tenant="acme",
        )
        try:
            print(await agent.run("remember this workspace handoff"))
            recalled = await agent._runtime._memory.recall("workspace handoff")
            tool_names = sorted(tool.__name__ for tool in agent._runtime._workspace_tools)
            print("recalled=", bool(recalled))
            print("workspace_tools=", ",".join(tool_names))
        finally:
            await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
