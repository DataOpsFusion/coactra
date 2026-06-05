from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic import BaseModel
from pydantic_ai.models.test import TestModel
from coactra.agent.sdk import Agent


def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("hello from the agent")])


class Plan(BaseModel):
    steps: list[str]


async def test_create_send_wait():
    agent = await Agent.create(model=FunctionModel(_final), instructions="be brief")
    run = await agent.send("hi")
    result = await run.wait()
    assert "hello from the agent" in result.text
    await agent.aclose()


async def test_run_structured():
    agent = await Agent.create(model=TestModel())
    plan = await agent.run("make a plan", output_type=Plan)
    assert isinstance(plan, Plan)
    await agent.aclose()


async def test_async_context_manager():
    async with await Agent.create(model=FunctionModel(_final)) as agent:
        run = await agent.send("hi")
        async for _ev in run.stream():
            pass
        assert (await run.wait()).status == "finished"
