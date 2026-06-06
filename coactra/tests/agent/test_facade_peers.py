"""TDD tests — peers= outbound delegation + agent.serve() via Agent facade.

RED first: run before wiring peers=/serve into facade → tests fail.
GREEN: wire peers= on Agent.create, Agent.serve(), and serve_agent export.

Offline: all model interactions use FunctionModel (no network).
"""
from __future__ import annotations

import pytest

from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart

from coactra.agent import Agent
from coactra.agent.skills import Skill

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _echo_model(name: str) -> FunctionModel:
    """FunctionModel that echoes back '<name>:<question>'."""

    def _reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        last_text = name
        for msg in reversed(messages):
            for part in getattr(msg, "parts", []):
                if hasattr(part, "content") and isinstance(part.content, str):
                    last_text = f"{name}:{part.content}"
                    break
            else:
                continue
            break
        return ModelResponse(parts=[TextPart(last_text)])

    return FunctionModel(_reply)


async def _make_peer(name: str, tenant: str) -> Agent:
    return await Agent.create(
        model=_echo_model(name),
        name=name,
        tenant=tenant,
        expose=True,
    )


# ---------------------------------------------------------------------------
# Test 1 — peers= wires ask_<peer> tool into main agent; direct invocation works
# ---------------------------------------------------------------------------


async def test_peers_tool_present_and_delegates():
    """peers= on Agent.create adds an ask_<peer> tool that delegates to the peer."""
    peer = await _make_peer("security-agent", "acme")
    main = await Agent.create(
        model=_echo_model("sre-1"),
        name="sre-1",
        tenant="acme",
        peers=[peer],
    )

    # The agent must expose _tools so we can assert the peer tool is wired in.
    tools = main._tools
    tool_names = [t.__name__ for t in tools]
    assert "ask_security_agent" in tool_names, (
        f"Expected ask_security_agent in tools, got: {tool_names}"
    )

    # Directly invoke the tool callable to verify delegation works.
    ask = next(t for t in tools if t.__name__ == "ask_security_agent")
    result = await ask("rotate cert")
    assert "rotate cert" in result, f"Expected 'rotate cert' in {result!r}"


# ---------------------------------------------------------------------------
# Test 2 — cross-tenant peer delegation is denied
# ---------------------------------------------------------------------------


async def test_peers_cross_tenant_denied():
    """A peer in a different tenant causes the delegation tool to refuse."""
    peer = await _make_peer("ext-agent", "other")  # tenant="other", caller tenant="acme"
    main = await Agent.create(
        model=_echo_model("sre-1"),
        name="sre-1",
        tenant="acme",
        peers=[peer],
    )

    ask = next(t for t in main._tools if t.__name__ == "ask_ext_agent")
    result = await ask("secret task")
    assert "not permitted" in result.lower() or "denied" in result.lower(), (
        f"Expected denial message, got: {result!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Agent.serve() and top-level serve_agent export
# ---------------------------------------------------------------------------

a2a = pytest.importorskip("a2a")
starlette = pytest.importorskip("starlette")


async def test_agent_serve_returns_app():
    """agent.serve() returns a non-None Starlette app; top-level import works."""
    from coactra import serve_agent as top_level_serve_agent  # noqa: PLC0415
    from starlette.applications import Starlette  # noqa: PLC0415

    agent = await Agent.create(
        model=_echo_model("helper"),
        name="helper",
        tenant="acme",
        skills=[Skill(id="general", description="general purpose agent")],
    )

    # agent.card must be non-None before we serve
    assert agent.card is not None

    # Method on the facade
    app = agent.serve()
    assert app is not None
    assert isinstance(app, Starlette)

    # Top-level export must resolve to the same underlying function
    app2 = top_level_serve_agent(agent)
    assert app2 is not None
    assert isinstance(app2, Starlette)
