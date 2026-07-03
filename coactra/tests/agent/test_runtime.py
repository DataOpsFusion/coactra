from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from coactra.agent.runtime import PydanticAIRuntime


async def _final_text(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
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


def test_runtime_str_model_passthrough():
    """String model ids are passed through to pydantic-ai unchanged."""
    rt = PydanticAIRuntime(model="openai:gpt-4o-mini")
    assert rt._model == "openai:gpt-4o-mini"


def test_runtime_model_instance_passthrough_ignores_provider_config():
    """When a Model instance is passed, provider config kwargs are ignored (no error)."""
    inner = TestModel()
    rt = PydanticAIRuntime(model=inner, api_base="https://ignored/v1", api_key="ignored")
    assert rt._model is inner


async def test_runtime_stream_failed_preserves_error_message():
    rt = PydanticAIRuntime(model=TestModel())
    mock_agent = MagicMock()
    mock_run = MagicMock()
    mock_run.__aenter__ = AsyncMock(side_effect=RuntimeError("boom-detail"))
    mock_agent.iter.return_value = mock_run
    rt._build = lambda *args, **kwargs: mock_agent  # type: ignore[method-assign]

    results: list = []

    async for _event in rt.stream("hi", run_id="r3", on_result=results.append):
        pass

    assert results
    assert results[-1].status == "error"
    assert results[-1].error == "boom-detail"
