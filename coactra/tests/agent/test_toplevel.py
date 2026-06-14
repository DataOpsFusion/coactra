"""Tests for top-level coactra imports and output= alias."""

from pydantic import BaseModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

import coactra
from coactra import (
    Agent,
    ModelProfile,
    ModelResolver,
    ModelRoute,
    Policy,
    RemotePeer,
    Run,
    Scope,
    Team,
)  # noqa: F401
from coactra.agent import MCPServer, mcp


def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("hello")])


class MyOutput(BaseModel):
    answer: str


async def _make_agent(*, model, tools=None):
    resolver = ModelResolver(
        [ModelRoute(capability="default", profile=ModelProfile(name="default", model=model))]
    )
    team = Team(
        scope=Scope(tenant_id="acme", namespace="toplevel"),
        policy=Policy.permissive(),
        model_resolver=resolver,
    )
    return await team.add_agent(model_capability="default", tools=tools, name="agent-under-test")


async def test_toplevel_import():
    assert Agent is not None
    assert RemotePeer is not None
    assert Run is not None
    assert Scope is not None
    assert coactra.__version__


async def test_toplevel_run():
    agent = await _make_agent(model=FunctionModel(_final))
    result = await agent.run("hi")
    assert result == "hello"
    await agent.aclose()


async def test_output_alias():
    agent = await _make_agent(model=TestModel())
    result = await agent.run("give me an answer", output=MyOutput)
    assert isinstance(result, MyOutput)
    await agent.aclose()


def test_mcp_helper_creates_remote_tool_tag():
    server = mcp("https://tools.example/mcp", name="extra")
    assert server.url == "https://tools.example/mcp"
    assert server.name == "extra"


def test_mcpserver_constructor_creates_remote_tool_tag():
    server = MCPServer(url="https://tools.example/mcp", name="extra")
    assert server.url == "https://tools.example/mcp"
    assert server.name == "extra"


async def test_team_add_agent_accepts_mcp_helper_tool():
    from pydantic_ai.mcp import MCPToolset

    agent = await _make_agent(
        model=FunctionModel(_final),
        tools=[mcp("https://tools.example/mcp", name="extra")],
    )
    assert len(agent._runtime._mcp_toolsets) == 1
    assert isinstance(agent._runtime._mcp_toolsets[0], MCPToolset)
    assert agent._tools == []
    await agent.aclose()


async def test_team_add_agent_accepts_mcpserver_tool():
    from pydantic_ai.mcp import MCPToolset

    agent = await _make_agent(
        model=FunctionModel(_final),
        tools=[MCPServer(url="https://tools.example/mcp", name="extra")],
    )
    assert len(agent._runtime._mcp_toolsets) == 1
    assert isinstance(agent._runtime._mcp_toolsets[0], MCPToolset)
    await agent.aclose()
