from pydantic import BaseModel
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from coactra.agent.runtime import PydanticAIRuntime
from coactra.agent.litellm_model import LiteLLMModel


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


# --- Provider config threading tests ---

def test_runtime_str_model_with_provider_config_reaches_litellm_model():
    """Provider config (api_base, api_key) must be forwarded to LiteLLMModel._call_kwargs."""
    rt = PydanticAIRuntime(
        model="openai/gpt-4o-mini",
        api_base="https://x/v1",
        api_key="k",
    )
    assert isinstance(rt._model, LiteLLMModel)
    assert rt._model._call_kwargs == {"api_base": "https://x/v1", "api_key": "k"}


def test_runtime_str_model_with_defaults_forwarded():
    """Extra **defaults (e.g. temperature) must also reach LiteLLMModel._call_kwargs."""
    rt = PydanticAIRuntime(
        model="openai/gpt-4o-mini",
        api_base="https://x/v1",
        api_key="k",
        temperature=0.1,
    )
    assert isinstance(rt._model, LiteLLMModel)
    assert rt._model._call_kwargs == {"api_base": "https://x/v1", "api_key": "k", "temperature": 0.1}


def test_runtime_model_instance_passthrough_ignores_provider_config():
    """When a Model instance is passed, provider config kwargs are ignored (no error)."""
    inner = TestModel()
    rt = PydanticAIRuntime(model=inner, api_base="https://ignored/v1", api_key="ignored")
    assert rt._model is inner
