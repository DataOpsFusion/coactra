"""Tests for top-level coactra imports and output= alias."""

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

import coactra
from coactra import Agent, RemotePeer, Run, Scope  # noqa: F401  — top-level import under test
from coactra.agent import MCPServer, mcp


def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("hello")])


class MyOutput(BaseModel):
    answer: str


async def test_toplevel_import():
    """from coactra import Agent, Run, Scope, __version__ must work."""
    assert Agent is not None
    assert RemotePeer is not None
    assert Run is not None
    assert Scope is not None
    assert coactra.__version__


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
    """mcp(url) tags additive remote MCP servers from coactra.agent."""
    server = mcp("https://tools.example/mcp", name="extra")
    assert server.url == "https://tools.example/mcp"
    assert server.name == "extra"


def test_mcpserver_constructor_creates_remote_tool_tag():
    """MCPServer(url=...) is the explicit alternative to mcp()."""
    server = MCPServer(url="https://tools.example/mcp", name="extra")
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


async def test_agent_create_accepts_mcpserver_tool():
    """Agent.create accepts MCPServer instances directly."""
    from pydantic_ai.mcp import MCPToolset

    agent = await Agent.create(
        model=FunctionModel(_final),
        tools=[MCPServer(url="https://tools.example/mcp", name="extra")],
    )
    assert len(agent._runtime._mcp_toolsets) == 1
    assert isinstance(agent._runtime._mcp_toolsets[0], MCPToolset)
    await agent.aclose()
