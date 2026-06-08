"""TDD tests for peers.py — outbound in-process peer delegation via peer_tools().

RED first: run with no implementation → import error / AttributeError.
GREEN: implement coactra/src/coactra/agent/peers.py.
"""

from __future__ import annotations

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra.agent import Agent
from coactra.agent.domain import AgentRef
from coactra.team import Team

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _echo_model(name: str):
    """Return a FunctionModel whose reply echoes the last user message."""

    def _reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        # Get the last user text
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
# Test 1 — same-tenant delegation works
# ---------------------------------------------------------------------------


async def test_peer_tools_delegation_works():
    """ask_<peer> calls the peer's agent.run and returns its output."""
    from coactra.agent.peers import peer_tools

    security_agent = await _make_peer("security-agent", "acme")
    team = Team([security_agent])

    tools = peer_tools(
        ["security-agent"],
        resolve=team.member,
        me="sre-1",
        tenant="acme",
    )

    assert len(tools) == 1
    tool = tools[0]
    # Tool must be named ask_security_agent (hyphen → underscore)
    assert tool.__name__ == "ask_security_agent"

    result = await tool("rotate cert")
    # The echo model returns "<name>:<question>"
    assert "rotate cert" in result


# ---------------------------------------------------------------------------
# Test 2 — cross-tenant delegation is denied
# ---------------------------------------------------------------------------


async def test_peer_tools_cross_tenant_is_denied():
    """A peer in a different tenant causes the tool to refuse."""
    from coactra.agent.peers import peer_tools

    # Peer is in "globex"; caller is "acme" → cross-tenant → denied.
    external_agent = await _make_peer("ext-agent", "globex")
    team = Team([external_agent])

    tools = peer_tools(
        ["ext-agent"],
        resolve=team.member,
        me="sre-1",
        tenant="acme",
    )

    assert len(tools) == 1
    tool = tools[0]

    # The tool must refuse — either raise an exception or return a "not permitted" string.
    try:
        result = await tool("secret task")
        # If it returns a string it must communicate denial, not the peer output
        assert "not permitted" in result.lower() or "denied" in result.lower()
    except Exception as exc:
        # Any exception (CollaborationDenied or similar) is also acceptable
        assert str(exc)  # must have a message


# ---------------------------------------------------------------------------
# Test 3 — resolve returning None does not crash; returns clear message
# ---------------------------------------------------------------------------


async def test_peer_tools_unresolved_peer_returns_not_found():
    """If resolve() returns None the tool returns a clear 'not found' message."""
    from coactra.agent.peers import peer_tools

    tools = peer_tools(
        ["ghost-agent"],
        resolve=lambda name: None,  # always returns None
        me="sre-1",
        tenant="acme",
    )

    assert len(tools) == 1
    tool = tools[0]

    try:
        result = await tool("ping")
        assert "not found" in result.lower() or "unavailable" in result.lower()
    except Exception as exc:
        assert str(exc)


# ---------------------------------------------------------------------------
# Test 4 — default policy (AllowSameTenant) is used when policy=None
# ---------------------------------------------------------------------------


async def test_peer_tools_default_policy_permits_same_tenant():
    """Default policy (no explicit policy=) permits same-tenant peers."""
    from coactra.agent.peers import peer_tools

    peer = await _make_peer("infra-agent", "acme")
    team = Team([peer])

    # policy defaults to AllowSameTenant
    tools = peer_tools(
        ["infra-agent"],
        resolve=team.member,
        me="sre-1",
        tenant="acme",
    )

    result = await tools[0]("check status")
    assert "check status" in result


# ---------------------------------------------------------------------------
# Test 5 — multiple peers produce multiple tools with correct names
# ---------------------------------------------------------------------------


async def test_peer_tools_multiple_peers():
    """peer_tools with N peers returns N tools with correct ask_<name> names."""
    from coactra.agent.peers import peer_tools

    agent_a = await _make_peer("alpha-agent", "acme")
    agent_b = await _make_peer("beta-agent", "acme")
    team = Team([agent_a, agent_b])

    tools = peer_tools(
        ["alpha-agent", "beta-agent"],
        resolve=team.member,
        me="orchestrator",
        tenant="acme",
    )

    assert len(tools) == 2
    names = {t.__name__ for t in tools}
    assert names == {"ask_alpha_agent", "ask_beta_agent"}

    # Each tool is independently callable
    for tool in tools:
        result = await tool("hello")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Test 6 — remote A2A delegation uses the provided transport
# ---------------------------------------------------------------------------


class RecordingTransport:
    def __init__(self) -> None:
        self.calls = []

    async def send(self, dst, question, scope):
        self.calls.append((dst, question, scope))
        return f"remote:{dst.qualified_name}:{question}"


async def test_peer_tools_remote_delegation_uses_transport_when_unresolved():
    """Unresolved peers can be delegated to remotely through an A2A transport."""
    from coactra.agent.peers import peer_tools

    transport = RecordingTransport()
    tools = peer_tools(
        [AgentRef(tenant_id="acme", agent_id="security-agent")],
        resolve=lambda name: None,
        transport=transport,
        me="sre-1",
        tenant="acme",
    )

    assert tools[0].__name__ == "ask_security_agent"

    result = await tools[0]("status?")

    assert result == "remote:acme/security-agent:status?"
    assert len(transport.calls) == 1
    dst, question, scope = transport.calls[0]
    assert dst == AgentRef(tenant_id="acme", agent_id="security-agent")
    assert question == "status?"
    assert scope.tenant_id == "acme"


async def test_peer_tools_remote_cross_tenant_is_denied_before_transport():
    """Remote A2A delegation is still same-tenant gated before the wire."""
    from coactra.agent.peers import peer_tools

    transport = RecordingTransport()
    tools = peer_tools(
        [AgentRef(tenant_id="globex", agent_id="external-agent")],
        resolve=lambda name: None,
        transport=transport,
        me="sre-1",
        tenant="acme",
    )

    result = await tools[0]("secret")

    assert "not permitted" in result.lower() or "denied" in result.lower()
    assert transport.calls == []
