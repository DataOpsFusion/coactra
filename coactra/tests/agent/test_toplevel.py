"""Tests for top-level coactra imports and output= alias."""
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic import BaseModel
from pydantic_ai.models.test import TestModel

from coactra import Agent, RemotePeer, Run, mcp  # noqa: F401  — top-level import under test


def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("hello")])


class MyOutput(BaseModel):
    answer: str


async def test_toplevel_import():
    """from coactra import Agent, Run must work."""
    assert Agent is not None
    assert RemotePeer is not None
    assert Run is not None
    assert mcp is not None


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


def test_mcp_helper_creates_remote_tool_tag():
    """mcp(url) is the public tag for additive remote MCP servers."""
    server = mcp("https://tools.example/mcp", name="extra")
    assert server.url == "https://tools.example/mcp"
    assert server.name == "extra"


async def test_agent_create_accepts_mcp_helper_tool():
    """Agent.create expands mcp(url) tool tags into additive MCP toolsets."""
    from pydantic_ai.mcp import MCPToolset

    agent = await Agent.create(
        model=FunctionModel(_final),
        tools=[mcp("https://tools.example/mcp", name="extra")],
    )
    assert len(agent._runtime._mcp_toolsets) == 1
    assert isinstance(agent._runtime._mcp_toolsets[0], MCPToolset)
    assert agent._tools == []
    await agent.aclose()
