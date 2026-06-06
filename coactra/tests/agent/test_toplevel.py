"""Tests for top-level coactra imports and output= alias."""
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic import BaseModel
from pydantic_ai.models.test import TestModel

from coactra import Agent, Run  # noqa: F401  — top-level import under test


def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("hello")])


class MyOutput(BaseModel):
    answer: str


async def test_toplevel_import():
    """from coactra import Agent, Run must work."""
    assert Agent is not None
    assert Run is not None


async def test_toplevel_run():
    """Agent imported from coactra top-level runs offline."""
    agent = await Agent.create(model=FunctionModel(_final))
    result = await agent.run("hi")
    assert result == "hello"
    await agent.aclose()


async def test_output_alias():
    """`output=` kwarg is accepted and returns a typed object."""
    agent = await Agent.create(model=TestModel())
    result = await agent.run("give me an answer", output=MyOutput)
    assert isinstance(result, MyOutput)
    await agent.aclose()
