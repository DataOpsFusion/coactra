from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from coactra.agent.sdk.runtime import PydanticAIRuntime
from coactra.agent.sdk.events import Assistant, ToolCall, ToolResult, Status


def _echo_tool(value: str) -> str:
    """Return the value unchanged."""
    return f"checked:{value}"


def _two_step(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    # 1st model call → ask to run the tool; 2nd → final text
    if len(messages) == 1:
        return ModelResponse(parts=[ToolCallPart("_echo_tool", {"value": "replication"})])
    return ModelResponse(parts=[TextPart("done: replication checked")])


async def test_stream_emits_tool_then_assistant():
    rt = PydanticAIRuntime(model=FunctionModel(_two_step), tools=[_echo_tool])
    kinds = []
    async for ev in rt.stream("check replication", run_id="r3"):
        kinds.append(type(ev).__name__)
    assert "ToolCall" in kinds
    assert "ToolResult" in kinds
    assert kinds[-1] == "Status"  # terminal
