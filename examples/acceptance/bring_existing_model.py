from __future__ import annotations

import asyncio

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import Agent


def existing_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("existing model handled it")])


async def main() -> None:
    agent = await Agent.create(model=FunctionModel(existing_model), instructions="Use host policy.")
    try:
        print(await agent.run("can I keep my own model?"))
    finally:
        await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
