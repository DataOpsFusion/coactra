"""TDD tests for peers.py — outbound delegation via peer_tools()."""

from __future__ import annotations

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team
from coactra.agent import Agent
from coactra.agent.domain import AgentRef


def _echo_model(name: str):
    async def _reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
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


def _team_with_model(tenant: str, model, capability: str = "default") -> Team:
    return Team(
        scope=Scope(tenant_id=tenant, namespace="peers"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [ModelRoute(capability=capability, profile=ModelProfile(name=capability, model=model))]
        ),
    )


async def _make_peer(name: str, tenant: str) -> Agent:
    team = _team_with_model(tenant, _echo_model(name))
    return await team.add_agent(model_capability="default", name=name, expose=True)


async def test_peer_tools_delegation_works():
    from coactra.agent.peers import peer_tools

    security_agent = await _make_peer("security-agent", "acme")
    team = _team_with_model("acme", _echo_model("unused"))
    team._members["security-agent"] = security_agent

    tools = peer_tools(
        ["security-agent"],
        resolve=team.member,
        policy=Policy.permissive(),
        me="sre-1",
        tenant="acme",
    )
    result = await tools[0]("rotate cert")
    assert "rotate cert" in result


async def test_peer_tools_cross_tenant_is_denied():
    from coactra.agent.peers import peer_tools

    external_agent = await _make_peer("ext-agent", "globex")
    team = _team_with_model("acme", _echo_model("unused"))
    team._members["ext-agent"] = external_agent

    tools = peer_tools(
        ["ext-agent"], resolve=team.member, policy=Policy.default_deny(), me="sre-1", tenant="acme"
    )
    result = await tools[0]("secret task")
    assert "not permitted" in result.lower() or "denied" in result.lower()


async def test_peer_tools_unresolved_peer_returns_not_found():
    from coactra.agent.peers import peer_tools

    tools = peer_tools(
        ["ghost-agent"],
        resolve=lambda name: None,
        policy=Policy.permissive(),
        me="sre-1",
        tenant="acme",
    )
    result = await tools[0]("ping")
    assert "not found" in result.lower() or "unavailable" in result.lower()


async def test_peer_tools_policy_permits_same_tenant():
    from coactra.agent.peers import peer_tools

    peer = await _make_peer("infra-agent", "acme")
    team = _team_with_model("acme", _echo_model("unused"))
    team._members["infra-agent"] = peer

    tools = peer_tools(
        ["infra-agent"], resolve=team.member, policy=Policy.permissive(), me="sre-1", tenant="acme"
    )
    result = await tools[0]("check status")
    assert "check status" in result


class RecordingTransport:
    def __init__(self) -> None:
        self.calls = []

    async def send(self, dst, question, scope):
        self.calls.append((dst, question, scope))
        return f"remote:{dst.qualified_name}:{question}"


async def test_peer_tools_remote_delegation_uses_transport_when_unresolved():
    from coactra.agent.peers import peer_tools

    transport = RecordingTransport()
    tools = peer_tools(
        [AgentRef(tenant_id="acme", agent_id="security-agent")],
        resolve=lambda name: None,
        policy=Policy.permissive(),
        transport=transport,
        me="sre-1",
        tenant="acme",
    )

    result = await tools[0]("status?")
    assert result == "remote:acme/security-agent:status?"
    assert len(transport.calls) == 1


async def test_peer_tools_remote_denied_before_transport():
    from coactra.agent.peers import peer_tools

    transport = RecordingTransport()
    tools = peer_tools(
        [AgentRef(tenant_id="globex", agent_id="external-agent")],
        resolve=lambda name: None,
        policy=Policy.default_deny(),
        transport=transport,
        me="sre-1",
        tenant="acme",
    )

    result = await tools[0]("secret")
    assert "not permitted" in result.lower() or "denied" in result.lower()
    assert transport.calls == []
