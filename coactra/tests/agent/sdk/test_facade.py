from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic import BaseModel
from pydantic_ai.models.test import TestModel
from coactra.agent.sdk import Agent


def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("hello from the agent")])


def _echo_tool(value: str) -> str:
    """Return the value unchanged."""
    return f"checked:{value}"


def _two_step(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    if len(messages) == 1:
        return ModelResponse(parts=[ToolCallPart("_echo_tool", {"value": "x"})])
    return ModelResponse(parts=[TextPart("done")])


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


async def test_wait_after_stream_is_not_lossy():
    """Streaming then awaiting must return the full result (messages + tool_calls),
    not a text-only derivation."""
    agent = await Agent.create(model=FunctionModel(_two_step), tools=[_echo_tool])
    run = await agent.send("check")
    async for _ev in run.stream():
        pass
    result = await run.wait()
    assert result.messages  # full message history, was () before
    assert len(result.tool_calls) == 1  # the tool call, was () before
    await agent.aclose()
