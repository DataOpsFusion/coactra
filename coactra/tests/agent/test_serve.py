"""TDD tests for serve.py — inbound A2A serving via serve_agent().

RED first: run with no implementation → import error.
GREEN: implement coactra/src/coactra/agent/serve.py.

a2a-sdk / starlette are optional extras — guard with importorskip so the
test skips cleanly when they are absent.
"""
from __future__ import annotations

import pytest

a2a = pytest.importorskip("a2a")
starlette = pytest.importorskip("starlette")

from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart  # noqa: E402

from coactra.agent import Agent  # noqa: E402
from coactra.agent.skills import Skill  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _static_model(reply: str):
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(reply)])

    return FunctionModel(_fn)


async def _make_agent_with_skills(name: str = "test-agent", tenant: str = "acme") -> Agent:
    return await Agent.create(
        model=_static_model(f"reply-from-{name}"),
        name=name,
        tenant=tenant,
        skills=[Skill(id="general", description="general purpose agent")],
        expose=True,
    )


# ---------------------------------------------------------------------------
# Test 1 — serve_agent returns a Starlette app (construction only)
# ---------------------------------------------------------------------------


async def test_serve_agent_returns_starlette_app():
    """serve_agent(agent) builds and returns a Starlette app without raising."""
    from coactra.agent.serve import serve_agent
    from starlette.applications import Starlette

    agent = await _make_agent_with_skills()
    app = serve_agent(agent)

    assert isinstance(app, Starlette), (
        f"Expected Starlette, got {type(app)}"
    )


# ---------------------------------------------------------------------------
# Test 2 — the app exposes the agent card route
# ---------------------------------------------------------------------------


async def test_serve_agent_app_has_agent_card_route():
    """The built app must include the /.well-known/agent-card.json route."""
    from coactra.agent.serve import serve_agent

    agent = await _make_agent_with_skills()
    app = serve_agent(agent)

    # Extract all registered URL paths from the app's route table
    paths = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if path:
            paths.append(path)

    assert any("agent-card" in p or ".well-known" in p for p in paths), (
        f"No agent-card route found. Routes: {paths}"
    )


# ---------------------------------------------------------------------------
# Test 3 — the app has at least one JSON-RPC route (tasks endpoint)
# ---------------------------------------------------------------------------


async def test_serve_agent_app_has_jsonrpc_route():
    """The built app must include the A2A JSON-RPC tasks endpoint."""
    from coactra.agent.serve import serve_agent
    from a2a.utils.constants import DEFAULT_RPC_URL

    agent = await _make_agent_with_skills()
    app = serve_agent(agent)

    paths = [getattr(r, "path", "") for r in app.routes]
    assert any(DEFAULT_RPC_URL in p or DEFAULT_RPC_URL == p for p in paths), (
        f"No JSON-RPC route at {DEFAULT_RPC_URL!r}. Routes: {paths}"
    )


# ---------------------------------------------------------------------------
# Test 4 — agent card content is reflected in the app
# ---------------------------------------------------------------------------


async def test_serve_agent_card_skills_propagated():
    """The agent's card (name, skills) is used when assembling the app."""
    from coactra.agent.serve import serve_agent

    agent = await _make_agent_with_skills(name="security-bot")
    # agent.card must be non-None because skills and expose=True are set
    assert agent.card is not None
    assert agent.card["name"] == "security-bot"

    # serve_agent must succeed — any error here is a bug
    app = serve_agent(agent)
    assert app is not None


# ---------------------------------------------------------------------------
# Test 5 — serve_agent with explicit verifier does not raise
# ---------------------------------------------------------------------------


async def test_serve_agent_with_verifier():
    """Passing a verifier skips insecure-mode warning."""
    from coactra.agent.serve import serve_agent

    class _FakeVerifier:
        def verify(
            self,
            auth_header: str,
            *,
            requested_capability: str,
            allowed_subject_prefixes=("",),
        ):
            return {"sub": "agent-x"}

    agent = await _make_agent_with_skills()
    app = serve_agent(agent, verifier=_FakeVerifier())
    assert app is not None


# ---------------------------------------------------------------------------
# Test 6 — agent with no card (no skills, no expose) raises clearly
# ---------------------------------------------------------------------------


async def test_serve_agent_no_card_raises():
    """An agent without a card cannot be served — serve_agent must raise ValueError."""
    from coactra.agent.serve import serve_agent

    # No skills, no expose → card is None
    bare_agent = await Agent.create(
        model=_static_model("hello"),
        name="bare-agent",
        tenant="acme",
    )
    assert bare_agent.card is None

    with pytest.raises((ValueError, RuntimeError)):
        serve_agent(bare_agent)


# ---------------------------------------------------------------------------
# Test 7 — current a2a-sdk expects protobuf AgentCard on HTTP routes
# ---------------------------------------------------------------------------

async def test_serve_agent_card_route_returns_json_with_current_sdk():
    """The official card route must serialize the served card, not HTTP 500."""
    from coactra.agent.serve import serve_agent
    from starlette.testclient import TestClient

    agent = await _make_agent_with_skills(name="security-agent")
    app = serve_agent(agent)

    with TestClient(app) as client:
        response = client.get("/.well-known/agent-card.json")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "security-agent"
    assert body["skills"][0]["id"] == "general"


async def test_serve_agent_url_is_published_in_official_card():
    """A served agent can publish the reachable A2A endpoint for SDK clients."""
    from coactra.agent.serve import serve_agent
    from starlette.testclient import TestClient

    agent = await _make_agent_with_skills(name="security-agent")
    app = serve_agent(agent, url="http://127.0.0.1:8123")

    with TestClient(app) as client:
        body = client.get("/.well-known/agent-card.json").json()

    assert body["supportedInterfaces"][0]["url"] == "http://127.0.0.1:8123"
    assert body["supportedInterfaces"][0]["protocolBinding"] == "JSONRPC"
