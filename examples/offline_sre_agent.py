"""Offline SRE agent using the optional SDK adapter.

This uses pydantic-ai's FunctionModel, so it does not call a network model.
Install `coactra[agent]` before running it.
"""

from __future__ import annotations

import asyncio

from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import Agent


def sre_model(messages, info: AgentInfo) -> ModelResponse:  # noqa: ARG001
    return ModelResponse(
        parts=[
            TextPart(
                "Check deploy diff, database saturation, queue depth, and rollback criteria."
            )
        ]
    )


async def main() -> None:
    agent = await Agent.create(
        model=FunctionModel(sre_model),
        instructions="You are a concise SRE incident assistant.",
    )
    try:
        run = await agent.send("Checkout latency doubled after release 0.7.4")
        async for event in run.stream():
            print(type(event).__name__, getattr(event, "text", ""))
        print("FINAL:", (await run.wait()).text)
    finally:
        await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
