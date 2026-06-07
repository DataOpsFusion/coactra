"""LiteLLMModel: a pydantic-ai Model that routes through litellm + coactra.ai's
thinking-model handling (Slice 2 — closes the SDK<->ai seam).

These drive the model offline: ``_completion`` is injected with a fake that returns
OpenAI-shaped responses, so no network and no real litellm import are needed.
"""
from types import SimpleNamespace as NS

from pydantic import BaseModel
from pydantic_ai import Agent as PydAgent

from coactra.agent.litellm_model import LiteLLMModel


def _msg(*, content=None, reasoning=None, tool_calls=None):
    return NS(content=content, reasoning_content=reasoning, tool_calls=tool_calls, role="assistant")


def _resp(*, content=None, reasoning=None, tool_calls=None, prompt=3, completion=5):
    return NS(
        choices=[NS(message=_msg(content=content, reasoning=reasoning, tool_calls=tool_calls),
                    finish_reason="stop")],
        usage=NS(prompt_tokens=prompt, completion_tokens=completion, total_tokens=prompt + completion),
        model="fake-model", id="resp-1", created=0,
    )


def _tool_call(name, args, *, call_id="c1"):
    return NS(id=call_id, type="function", function=NS(name=name, arguments=args))


async def test_run_returns_reasoning_content_when_content_empty():
    """The headline thinking-model case: provider leaves ``content`` empty and puts the
    answer in ``reasoning_content``. The SDK agent must still return the answer."""
    resp = _resp(content="", reasoning="The answer is 42.")
    model = LiteLLMModel("openai/gpt-4o-mini", _completion=lambda **kw: resp)

    result = await PydAgent(model).run("what is the answer?")

    assert result.output == "The answer is 42."


async def test_tool_call_round_trip():
    """The model requests a tool call, pydantic-ai executes it, the return is mapped back
    to a litellm ``tool`` message, and the second turn produces the final answer."""
    turns = iter([
        _resp(tool_calls=[_tool_call("add", '{"a": 2, "b": 3}')]),
        _resp(content="The sum is 5."),
    ])
    seen: list[list[dict]] = []

    def fake(**kw):
        seen.append(kw["messages"])
        return next(turns)

    def add(a: int, b: int) -> int:
        return a + b

    model = LiteLLMModel("openai/gpt-4o-mini", _completion=fake)
    result = await PydAgent(model, tools=[add]).run("add 2 and 3")

    assert result.output == "The sum is 5."
    # second call must carry the tool result back to the provider as a `tool` message
    assert any(m.get("role") == "tool" for m in seen[1])


class _Weather(BaseModel):
    city: str
    temp_c: int


async def test_structured_output():
    """An ``output_type`` run: the model calls the output tool and the SDK returns the
    parsed, typed object."""
    resp = _resp(tool_calls=[_tool_call("final_result", '{"city": "Paris", "temp_c": 18}')])
    model = LiteLLMModel("openai/gpt-4o-mini", _completion=lambda **kw: resp)

    result = await PydAgent(model, output_type=_Weather).run("weather in Paris?")

    assert result.output == _Weather(city="Paris", temp_c=18)


async def test_passes_tool_schema_to_litellm():
    """Real providers need the tool schema to call a tool, so request() must forward the
    function tools to litellm as OpenAI tool params."""
    captured: dict = {}

    def fake(**kw):
        captured.update(kw)
        return _resp(content="ok")

    def add(a: int, b: int) -> int:
        return a + b

    model = LiteLLMModel("openai/gpt-4o-mini", _completion=fake)
    await PydAgent(model, tools=[add]).run("hi")

    names = [t["function"]["name"] for t in captured.get("tools", [])]
    assert "add" in names


def test_runtime_wraps_string_model_in_litellm():
    from coactra.agent.runtime import PydanticAIRuntime

    rt = PydanticAIRuntime(model="anthropic/claude-sonnet-4-5")

    assert isinstance(rt._model, LiteLLMModel)
    assert rt._model.model_name == "anthropic/claude-sonnet-4-5"


def test_runtime_passes_through_model_instance():
    from pydantic_ai.models.test import TestModel

    from coactra.agent.runtime import PydanticAIRuntime

    tm = TestModel()
    rt = PydanticAIRuntime(model=tm)

    assert rt._model is tm
