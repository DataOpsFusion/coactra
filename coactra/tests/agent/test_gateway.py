"""TDD tests for Task 3b — gateway-first, token-sliced MCP tools.

All tests are offline — no live network connections.
"""
from __future__ import annotations

import pytest
import httpx
from pydantic_ai.models.function import FunctionModel, AgentInfo
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart

from coactra.agent.auth import BearerAuth, StaticToken
from coactra.agent.runtime import PydanticAIRuntime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _final(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[TextPart("done")])


# ---------------------------------------------------------------------------
# 1. BearerAuth injects the correct Authorization header
# ---------------------------------------------------------------------------

async def test_bearer_auth_injects_static_token() -> None:
    """BearerAuth with StaticToken sets Authorization header on first yield."""
    auth = BearerAuth(StaticToken("t1"))
    # Must be a true httpx.Auth subclass — httpx._build_auth does isinstance(auth, Auth)
    assert isinstance(auth, httpx.Auth)
    request = httpx.Request("GET", "http://x")
    gen = auth.async_auth_flow(request)
    yielded = await gen.__anext__()
    assert yielded.headers["Authorization"] == "Bearer t1"
    # Clean up the generator
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()


async def test_bearer_auth_refreshes_token_per_flow() -> None:
    """Each separate async_auth_flow call fetches a fresh token from the source."""

    class _TwoShot:
        def __init__(self) -> None:
            self._calls = 0

        async def token(self) -> str:
            self._calls += 1
            return f"t{self._calls}"

    source = _TwoShot()
    auth = BearerAuth(source)

    # First flow → t1
    req1 = httpx.Request("GET", "http://x")
    gen1 = auth.async_auth_flow(req1)
    out1 = await gen1.__anext__()
    assert out1.headers["Authorization"] == "Bearer t1"

    # Second flow → t2
    req2 = httpx.Request("GET", "http://x")
    gen2 = auth.async_auth_flow(req2)
    out2 = await gen2.__anext__()
    assert out2.headers["Authorization"] == "Bearer t2"


# ---------------------------------------------------------------------------
# 2. Gateway wiring (white-box, no connect)
# ---------------------------------------------------------------------------

def test_gateway_wiring_creates_mcp_server() -> None:
    """When gateway= is provided, the runtime stores an MCPToolset and records the URL."""
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
    """When gateway= is absent, no MCP toolset is created."""
    rt = PydanticAIRuntime(model=FunctionModel(_final))
    assert rt._gateway_toolset is None


def test_gateway_wiring_str_auth_normalized_to_static_token() -> None:
    """A str auth value is normalized to StaticToken — still creates MCPToolset."""
    from pydantic_ai.mcp import MCPToolset

    rt = PydanticAIRuntime(
        model=FunctionModel(_final),
        gateway="https://gw/mcp",
        auth="my-static-token",
    )
    assert rt._gateway_toolset is not None
    assert isinstance(rt._gateway_toolset, MCPToolset)


def test_gateway_no_auth_uses_plain_client() -> None:
    """gateway= without auth= still creates an MCPToolset (no BearerAuth)."""
    from pydantic_ai.mcp import MCPToolset

    rt = PydanticAIRuntime(
        model=FunctionModel(_final),
        gateway="https://gw/mcp",
        auth=None,
    )
    assert rt._gateway_toolset is not None
    assert isinstance(rt._gateway_toolset, MCPToolset)


# ---------------------------------------------------------------------------
# 3. Offline agent still runs without gateway (no regression)
# ---------------------------------------------------------------------------

async def test_offline_agent_runs_without_gateway() -> None:
    """An agent created without gateway= still runs successfully."""
    rt = PydanticAIRuntime(model=FunctionModel(_final), instructions="be terse")
    result = await rt.run("hello", run_id="r-nogw")
    assert result.status == "finished"
    assert "done" in result.text


# ---------------------------------------------------------------------------
# 4. Facade Agent.create forwards gateway= and auth= params
# ---------------------------------------------------------------------------

async def test_agent_create_accepts_gateway_params() -> None:
    """Agent.create(gateway=, auth=) must not raise TypeError."""
    from coactra.agent import Agent

    # This should not raise — gateway param must be accepted
    agent = await Agent.create(
        model=FunctionModel(_final),
        gateway="https://gw/mcp",
        auth=StaticToken("t"),
    )
    # The internal runtime must have wired the gateway toolset
    from pydantic_ai.mcp import MCPToolset
    assert isinstance(agent._runtime._gateway_toolset, MCPToolset)
    await agent.aclose()


async def test_agent_aclose_without_gateway_is_harmless() -> None:
    """aclose() with no gateway must complete without error."""
    from coactra.agent import Agent

    agent = await Agent.create(model=FunctionModel(_final))
    await agent.aclose()  # should not raise
