"""Tests for peers= outbound delegation via the Team-first facade."""

from __future__ import annotations

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import (
    Decision,
    DecisionOutcome,
    ModelProfile,
    ModelResolver,
    ModelRoute,
    Policy,
    PolicyRequest,
    Scope,
    Team,
)
from coactra.agent import Agent


def _echo_model(name: str) -> FunctionModel:
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


def _team(tenant: str, model, capability: str = "default", policy=None) -> Team:
    return Team(
        scope=Scope(tenant_id=tenant, namespace="peers"),
        policy=policy or Policy.permissive(),
        model_resolver=ModelResolver(
            [ModelRoute(capability=capability, profile=ModelProfile(name=capability, model=model))]
        ),
    )


class CrossTenantDenyPolicy:
    async def check(self, request: PolicyRequest) -> Decision:
        if request.action == "model.use":
            return Decision(outcome=DecisionOutcome.allow, source="test")
        if request.action == "agent.delegate" and request.context.get(
            "src_tenant"
        ) != request.context.get("dst_tenant"):
            return Decision(
                outcome=DecisionOutcome.deny, reason="cross-tenant denied", source="test"
            )
        return Decision(outcome=DecisionOutcome.allow, source="test")


async def _make_peer(name: str, tenant: str) -> Agent:
    team = _team(tenant, _echo_model(name))
    return await team.add_agent(model_capability="default", name=name, expose=True)


async def _make_main(*, tenant: str = "acme", peers=None, policy=None):
    team = _team(tenant, _echo_model("sre-1"), policy=policy)
    return await team.add_agent(model_capability="default", name="sre-1", peers=peers)


async def test_peers_tool_present_and_delegates():
    peer = await _make_peer("security-agent", "acme")
    main = await _make_main(peers=[peer])
    ask = next(t for t in main._tools if t.__name__ == "ask_security_agent")
    result = await ask("rotate cert")
    assert "rotate cert" in result


async def test_peers_cross_tenant_denied():
    peer = await _make_peer("ext-agent", "other")
    main = await _make_main(tenant="acme", peers=[peer], policy=CrossTenantDenyPolicy())
    ask = next(t for t in main._tools if t.__name__ == "ask_ext_agent")
    result = await ask("secret task")
    assert "not permitted" in result.lower() or "denied" in result.lower()


class RecordingA2AClient:
    def __init__(self) -> None:
        self.calls = []

    async def call(self, **kwargs):
        self.calls.append(kwargs)
        return f"remote:{kwargs['agent_id']}:{kwargs['message']}"


async def test_team_add_agent_remote_peer_wires_official_a2a_transport():
    from coactra.agent import RemotePeer

    client = RecordingA2AClient()
    remote = RemotePeer(
        name="security-agent",
        endpoint="http://127.0.0.1:9999/a2a",
        audience="security-audience",
        client=client,
    )
    main = await _make_main(peers=[remote])

    ask = next(t for t in main._tools if t.__name__ == "ask_security_agent")
    result = await ask("triage incident")

    assert result == "remote:security-agent:triage incident"
    assert client.calls == [
        {
            "agent_id": "security-agent",
            "endpoint": "http://127.0.0.1:9999/a2a",
            "audience": "security-audience",
            "message": "triage incident",
            "delegation_chain": [],
        }
    ]


async def test_team_add_agent_peer_name_does_not_crash_and_reports_unavailable():
    main = await _make_main(peers=["security-agent"])

    ask = next(t for t in main._tools if t.__name__ == "ask_security_agent")
    result = await ask("triage incident")
    assert "unavailable" in result.lower()
