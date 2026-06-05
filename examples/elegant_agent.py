"""Runnable offline demo of the elegant Agent SDK (Slice 1).

Uses pydantic-ai's FunctionModel so it runs with no API key or network.
With a real model id (e.g. "anthropic/claude-sonnet-4-6") and ANTHROPIC_API_KEY,
swap `model=` for the string to call a real model.
"""
import asyncio

from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelResponse, TextPart

from coactra.agent.sdk import Agent


def _model(messages, info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("first check: replication lag; second: slow queries")])


async def main() -> None:
    agent = await Agent.create(model=FunctionModel(_model), instructions="SRE triage, be terse")
    run = await agent.send("triage db latency")
    async for ev in run.stream():
        print(type(ev).__name__, getattr(ev, "text", ""))
    print("FINAL:", (await run.wait()).text)
    await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
