"""Fleet registry tests for named remote peer discovery."""

from __future__ import annotations

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from coactra.agent import Agent


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


class RecordingA2AClient:
    def __init__(self) -> None:
        self.calls = []

    async def call(self, **kwargs):
        self.calls.append(kwargs)
        return f"remote:{kwargs['agent_id']}:{kwargs['message']}"


async def test_agent_create_peer_name_resolves_through_registry():
    """Named peers can resolve through a fleet registry into remote A2A tools."""
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

    main = await Agent.create(
        model=_echo_model("sre-1"),
        name="sre-1",
        tenant="acme",
        peers=["security-agent"],
        registry=registry,
    )

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


async def test_agent_create_rejects_invalid_peer_config():
    with pytest.raises(TypeError, match="peers must contain"):
        await Agent.create(model=_echo_model("sre-1"), peers=[None])


async def test_agent_create_rejects_duplicate_local_peer_names():
    peer_a = await Agent.create(model=_echo_model("security-a"), name="security", tenant="acme")
    peer_b = await Agent.create(model=_echo_model("security-b"), name="security", tenant="acme")

    with pytest.raises(ValueError, match="duplicate local peer name"):
        await Agent.create(
            model=_echo_model("sre-1"),
            name="sre-1",
            tenant="acme",
            peers=[peer_a, peer_b],
        )
