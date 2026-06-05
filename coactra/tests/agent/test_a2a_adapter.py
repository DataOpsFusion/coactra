from __future__ import annotations

import asyncio

from coactra.agent.adapters.a2a import A2ATransport, OfficialA2ATransport
from coactra.agent.domain import AgentRef, Scope
from coactra.agent.collaboration import AsyncA2ATransportPort


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def call(self, *, agent_id, endpoint, audience, message, delegation_chain=None):
        self.calls.append(
            {
                "agent_id": agent_id,
                "endpoint": endpoint,
                "audience": audience,
                "message": message,
                "delegation_chain": delegation_chain,
            }
        )
        return "ok"


def test_official_a2a_transport_satisfies_async_port() -> None:
    client = RecordingClient()
    transport = OfficialA2ATransport(
        client=client,
        endpoint_for=lambda ref: f"https://{ref.agent_id}.example/a2a",
        audience_for=lambda ref: f"a2a://{ref.agent_id}",
    )

    assert isinstance(transport, AsyncA2ATransportPort)
    assert A2ATransport is OfficialA2ATransport


def test_official_a2a_transport_sends_resolved_message() -> None:
    client = RecordingClient()
    transport = OfficialA2ATransport(
        client=client,
        endpoint_for=lambda ref: f"https://{ref.agent_id}.example/a2a",
        audience_for=lambda ref: f"a2a://{ref.agent_id}",
        delegation_chain=[{"agent_id": "manager"}],
        message_builder=lambda question: {"capability": "consult", "params": {"question": question}},
    )

    result = asyncio.run(
        transport.send(
            AgentRef(tenant_id="acme", agent_id="platform-agent"),
            "status?",
            Scope(tenant_id="acme", namespace="manager"),
        )
    )

    assert result == "ok"
    assert client.calls == [
        {
            "agent_id": "platform-agent",
            "endpoint": "https://platform-agent.example/a2a",
            "audience": "a2a://platform-agent",
            "message": {"capability": "consult", "params": {"question": "status?"}},
            "delegation_chain": [{"agent_id": "manager"}],
        }
    ]
