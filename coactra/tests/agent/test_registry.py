"""Fleet registry tests for named remote peer discovery."""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra import Policy, Scope, Team
from coactra.model import ModelProfile, ModelResolver, ModelRoute


def _echo_model(name: str) -> FunctionModel:
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


def _team(namespace: str, model, capability: str = "default") -> Team:
    return Team(
        scope=Scope(tenant_id="acme", namespace=namespace),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [ModelRoute(capability=capability, profile=ModelProfile(name=capability, model=model))]
        ),
    )


class RecordingA2AClient:
    def __init__(self) -> None:
        self.calls = []

    async def call(self, **kwargs):
        self.calls.append(kwargs)
        return f"remote:{kwargs['agent_id']}:{kwargs['message']}"


async def test_team_add_agent_peer_name_resolves_through_registry():
    from coactra.agent.registry import InMemoryFleetRegistry

    client = RecordingA2AClient()
    registry = InMemoryFleetRegistry()
    registry.register(
        name="security-agent",
        endpoint="http://127.0.0.1:9999/a2a",
        tenant="acme",
        audience="security-audience",
        client=client,
    )

    team = _team("registry", _echo_model("sre-1"))
    main = await team.add_agent( name="sre-1", peers=["security-agent"], registry=registry
    )

    ask = next(t for t in main._tools if t.__name__ == "ask_security_agent")
    result = await ask("triage incident")
    assert result == "remote:security-agent:triage incident"


async def test_team_add_agent_rejects_invalid_peer_config():
    team = _team("registry", _echo_model("sre-1"))
    with pytest.raises(TypeError, match="peers must contain"):
        await team.add_agent(model_capability="default", name="sre-1", peers=[None])


async def test_team_add_agent_rejects_duplicate_local_peer_names():
    team_a = _team("registry", _echo_model("security-a"))
    peer_a = await team_a.add_agent(model_capability="default", name="security")
    team_b = _team("registry", _echo_model("security-b"))
    peer_b = await team_b.add_agent(model_capability="default", name="security")

    main_team = _team("registry", _echo_model("sre-1"))
    with pytest.raises(ValueError, match="duplicate local peer name"):
        await main_team.add_agent(model_capability="default", name="sre-1", peers=[peer_a, peer_b])
