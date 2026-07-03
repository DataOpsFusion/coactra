from __future__ import annotations

import asyncio

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team


def existing_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("existing model handled it")])


async def main() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="acceptance"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver([
            ModelRoute(capability="existing-model", profile=ModelProfile(name="existing-model", model=FunctionModel(existing_model)))
        ]),
    )
    agent = await team.add_agent(
        model_capability="existing-model",
        name="existing-model-agent",
        instructions="Use host policy.",
    )
    try:
        print("existing_model_attached=", agent._runtime._model is not None)
    finally:
        await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
