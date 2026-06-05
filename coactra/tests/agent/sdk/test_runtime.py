from pydantic import BaseModel
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from coactra.agent.sdk.runtime import PydanticAIRuntime


def _final_text(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("the first check is replication lag")])


async def test_runtime_run_returns_text():
    rt = PydanticAIRuntime(model=FunctionModel(_final_text), instructions="be terse")
    result = await rt.run("triage db latency", run_id="r1")
    assert result.status == "finished"
    assert "replication lag" in result.text


class TriagePlan(BaseModel):
    steps: list[str]


async def test_runtime_structured_output():
    rt = PydanticAIRuntime(model=TestModel())  # TestModel fabricates schema-valid data
    result = await rt.run("plan", run_id="r2", output_type=TriagePlan)
    assert result.status == "finished"
    assert isinstance(result.output, TriagePlan)
    assert isinstance(result.output.steps, list)
