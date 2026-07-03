from __future__ import annotations

import asyncio
import tempfile

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team


def existing_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("memory and workspace stayed external")])


async def main() -> None:
    with tempfile.TemporaryDirectory() as desk:
        team = Team(
            scope=Scope(tenant_id="acme", namespace="acceptance"),
            policy=Policy.permissive(),
            model_resolver=ModelResolver([
                ModelRoute(capability="support", profile=ModelProfile(name="support", model=FunctionModel(existing_model)))
            ]),
        )
        agent = await team.add_agent(
            model_capability="support",
            memory="inprocess",
            workspace=desk,
            name="support-agent",
        )
        try:
            await agent._runtime._memory.remember("workspace handoff")
            recalled = await agent._runtime._memory.recall("workspace handoff")
            tools = {tool.__name__: tool for tool in agent._runtime._workspace_tools}
            tools["write_file"]("handoff.txt", "workspace handoff")
            read_back = tools["read_file"]("handoff.txt")
            tool_names = sorted(tools)
            print("recalled=", bool(recalled))
            print("workspace_read=", read_back)
            print("workspace_tools=", ",".join(tool_names))
        finally:
            await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
