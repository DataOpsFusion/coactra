from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team


async def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("hello from the agent")])


async def _echo_tool(value: str) -> str:
    return f"checked:{value}"


async def _two_step(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    if len(messages) == 1:
        return ModelResponse(parts=[ToolCallPart("_echo_tool", {"value": "x"})])
    return ModelResponse(parts=[TextPart("done")])


class Plan(BaseModel):
    steps: list[str]


async def _make_agent(*, model, name: str = "facade-agent", **kwargs):
    resolver = ModelResolver(
        [ModelRoute(capability="default", profile=ModelProfile(name="default", model=model))]
    )
    team = Team(
        scope=Scope(tenant_id="acme", namespace="facade"),
        policy=Policy.permissive(),
        model_resolver=resolver,
    )
    return await team.add_agent(model_capability="default", name=name, **kwargs)


async def test_create_send_wait():
    agent = await _make_agent(model=FunctionModel(_final), instructions="be brief")
    run = await agent.send("hi")
    result = await run.wait()
    assert "hello from the agent" in result.text
    await agent.aclose()


async def test_run_structured():
    agent = await _make_agent(model=TestModel())
    plan = await agent.run("make a plan", output_type=Plan)
    assert isinstance(plan, Plan)
    await agent.aclose()


async def test_run_output_type_str_returns_text():
    agent = await _make_agent(model=FunctionModel(_final))
    text = await agent.run("hi", output_type=str)
    assert text == "hello from the agent"
    await agent.aclose()


async def test_async_context_manager():
    async with await _make_agent(model=FunctionModel(_final)) as agent:
        run = await agent.send("hi")
        async for _ev in run.stream():
            pass
        assert (await run.wait()).status == "finished"


async def test_wait_after_stream_is_not_lossy():
    agent = await _make_agent(model=FunctionModel(_two_step), tools=[_echo_tool])
    run = await agent.send("check")
    async for _ev in run.stream():
        pass
    result = await run.wait()
    assert result.messages
    assert len(result.tool_calls) == 1
    await agent.aclose()
