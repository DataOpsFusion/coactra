from __future__ import annotations

import asyncio

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team
from coactra.agent import MCPServer


def existing_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("mcp toolset attached")])


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="acceptance"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(capability="toolset", profile=ModelProfile(name="toolset", model=FunctionModel(existing_model)))
        ]),
    )
    agent = await team.add_agent(
        model_capability="toolset",
        name="toolset-agent",
        tools=[MCPServer(url="https://tools.example/mcp", name="existing-tools")],
    )
    try:
        print("mcp_toolsets=", len(agent._runtime._mcp_toolsets))
    finally:
        await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
