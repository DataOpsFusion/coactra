from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra.agent.runtime import PydanticAIRuntime


async def _echo_tool(value: str) -> str:
    """Return the value unchanged."""
    return f"checked:{value}"


async def _two_step(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    # 1st model call → ask to run the tool; 2nd → final text
    if len(messages) == 1:
        return ModelResponse(parts=[ToolCallPart("_echo_tool", {"value": "replication"})])
    return ModelResponse(parts=[TextPart("done: replication checked")])


async def _final_text(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("all done")])


async def test_stream_emits_tool_then_assistant():
    rt = PydanticAIRuntime(model=FunctionModel(_two_step), tools=[_echo_tool])
    kinds = []
    async for ev in rt.stream("check replication", run_id="r3"):
        kinds.append(type(ev).__name__)
    assert "ToolCall" in kinds
    assert "ToolResult" in kinds
    assert kinds[-1] == "Status"  # terminal


async def test_stream_emits_usage_event():
    rt = PydanticAIRuntime(model=FunctionModel(_final_text))
    kinds = [type(ev).__name__ async for ev in rt.stream("hi", run_id="r4")]
    assert "Usage" in kinds
    assert kinds[-1] == "Status"  # usage comes before the terminal status
