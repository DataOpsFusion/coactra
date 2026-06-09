"""TDD tests for Task 3b — gateway-first, token-sliced MCP tools."""

from __future__ import annotations

import httpx
import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team
from coactra.agent.auth import BearerAuth, StaticToken
from coactra.agent.runtime import PydanticAIRuntime


def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("done")])


async def test_bearer_auth_injects_static_token() -> None:
    auth = BearerAuth(StaticToken("t1"))
    assert isinstance(auth, httpx.Auth)
    request = httpx.Request("GET", "http://x")
    gen = auth.async_auth_flow(request)
    yielded = await gen.__anext__()
    assert yielded.headers["Authorization"] == "Bearer t1"
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_bearer_auth_refreshes_token_per_flow() -> None:
    class _TwoShot:
        def __init__(self) -> None:
            self._calls = 0

        async def token(self) -> str:
            self._calls += 1
            return f"t{self._calls}"

    source = _TwoShot()
    auth = BearerAuth(source)
    req1 = httpx.Request("GET", "http://x")
    gen1 = auth.async_auth_flow(req1)
    out1 = await gen1.__anext__()
    assert out1.headers["Authorization"] == "Bearer t1"
    req2 = httpx.Request("GET", "http://x")
    gen2 = auth.async_auth_flow(req2)
    out2 = await gen2.__anext__()
    assert out2.headers["Authorization"] == "Bearer t2"


def test_gateway_wiring_creates_mcp_server() -> None:
    from pydantic_ai.mcp import MCPToolset

    rt = PydanticAIRuntime(
        model=FunctionModel(_final),
        gateway="https://gw/mcp",
        auth=StaticToken("t"),
    )
    assert rt._gateway_toolset is not None
    assert isinstance(rt._gateway_toolset, MCPToolset)
    assert rt._gateway_url == "https://gw/mcp"


def test_gateway_wiring_no_gateway_has_no_server() -> None:
    rt = PydanticAIRuntime(model=FunctionModel(_final))
    assert rt._gateway_toolset is None


def test_gateway_wiring_str_auth_normalized_to_static_token() -> None:
    from pydantic_ai.mcp import MCPToolset

    rt = PydanticAIRuntime(
        model=FunctionModel(_final),
        gateway="https://gw/mcp",
        auth="my-static-token",
    )
    assert rt._gateway_toolset is not None
    assert isinstance(rt._gateway_toolset, MCPToolset)


def test_gateway_no_auth_uses_plain_client() -> None:
    from pydantic_ai.mcp import MCPToolset

    rt = PydanticAIRuntime(
        model=FunctionModel(_final),
        gateway="https://gw/mcp",
        auth=None,
    )
    assert rt._gateway_toolset is not None
    assert isinstance(rt._gateway_toolset, MCPToolset)


async def test_offline_agent_runs_without_gateway() -> None:
    rt = PydanticAIRuntime(model=FunctionModel(_final), instructions="be terse")
    result = await rt.run("hello", run_id="r-nogw")
    assert result.status == "finished"
    assert "done" in result.text


async def test_team_add_agent_accepts_gateway_params() -> None:
    from pydantic_ai.mcp import MCPToolset

    team = Team(
        scope=Scope(tenant_id="acme", namespace="gateway"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="default",
                    profile=ModelProfile(name="default", model=FunctionModel(_final)),
                )
            ]
        ),
    )
    agent = await team.add_agent(
        model_capability="default",
        gateway="https://gw/mcp",
        auth=StaticToken("t"),
        name="gateway-agent",
    )
    assert isinstance(agent._runtime._gateway_toolset, MCPToolset)
    await agent.aclose()


async def test_agent_aclose_without_gateway_is_harmless() -> None:
    team = Team(
        scope=Scope(tenant_id="acme", namespace="gateway"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="default",
                    profile=ModelProfile(name="default", model=FunctionModel(_final)),
                )
            ]
        ),
    )
    agent = await team.add_agent(model_capability="default", name="nogw-agent")
    await agent.aclose()


def test_build_mcp_toolsets_returns_gateway_and_additive_servers() -> None:
    from pydantic_ai.mcp import MCPToolset

    from coactra.agent.domain.tools import mcp
    from coactra.agent.toolsets import build_mcp_toolsets

    gateway_toolset, additive = build_mcp_toolsets(
        gateway="https://gw/mcp",
        auth="token",
        mcp_servers=[mcp("https://extra/mcp", name="extra")],
    )

    assert isinstance(gateway_toolset, MCPToolset)
    assert len(additive) == 1
    assert isinstance(additive[0], MCPToolset)
