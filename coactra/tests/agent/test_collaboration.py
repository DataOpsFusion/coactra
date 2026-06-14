import asyncio

import pytest

from coactra import Decision, DecisionOutcome, Policy, PolicyRequest
from coactra.agent import (
    AgentRef,
    AsyncA2ATransportPort,
    AsyncPolicyGatedCollaborator,
    CollaborationDenied,
    Scope,
)


class AsyncFakeTransport:
    def __init__(self):
        self.sent = []

    async def send(self, dst, question, scope):
        self.sent.append((dst.agent_id, question, dst.tenant_id))
        return f"{dst.agent_id}:ack"


class TenantOnlyPolicy:
    async def check(self, request: PolicyRequest) -> Decision:
        principal = request.principal.split(":", 1)[1]
        target = request.resource.split(":", 1)[1]
        src_tenant = request.context.get("src_tenant")
        dst_tenant = request.context.get("dst_tenant")
        if src_tenant != dst_tenant:
            return Decision(outcome=DecisionOutcome.deny, reason="cross-tenant denied")
        if principal == "agent:a" and target.endswith("agent:b"):
            return Decision(outcome=DecisionOutcome.allow, source="test")
        return Decision(outcome=DecisionOutcome.deny, reason="pair denied", source="test")


ACME = Scope(tenant_id="acme")


def test_transport_protocol_only():
    assert isinstance(AsyncFakeTransport(), AsyncA2ATransportPort)


def test_async_policy_gated_collaborator_sends_when_allowed():
    t = AsyncFakeTransport()
    c = AsyncPolicyGatedCollaborator(
        transport=t, policy=TenantOnlyPolicy(), scope=ACME, me="agent:a"
    )
    reply = asyncio.run(c.ask("agent:b", "is it safe?", {}))
    assert reply == "agent:b:ack"
    assert t.sent == [("agent:b", "is it safe?", "acme")]


def test_async_denied_talk_raises_and_never_hits_the_wire():
    class DenyAll:
        async def check(self, request: PolicyRequest) -> Decision:
            return Decision(outcome=DecisionOutcome.deny, reason="no")

    t = AsyncFakeTransport()
    c = AsyncPolicyGatedCollaborator(transport=t, policy=DenyAll(), scope=ACME, me="agent:a")
    with pytest.raises(CollaborationDenied):
        asyncio.run(c.ask("agent:b", "hi", {}))
    assert t.sent == []


def test_async_cross_tenant_ask_never_hits_the_wire():
    t = AsyncFakeTransport()
    c = AsyncPolicyGatedCollaborator(
        transport=t, policy=TenantOnlyPolicy(), scope=ACME, me="agent:a"
    )
    with pytest.raises(CollaborationDenied):
        asyncio.run(c.ask(AgentRef(tenant_id="globex", agent_id="agent:b"), "hi", {}))
    assert t.sent == []


def test_async_collaborator_satisfies_escalation_router_shape():
    c = AsyncPolicyGatedCollaborator(
        transport=AsyncFakeTransport(), policy=TenantOnlyPolicy(), scope=ACME, me="agent:a"
    )

    class Esc:
        reason = "stuck"

    assert c.route(Esc(), chain=["manager", "human"]) == "human"


def test_policy_is_runtime_checkable_protocol_shape():
    class AllowAll:
        async def check(self, request: PolicyRequest) -> Decision:
            return Decision(outcome=DecisionOutcome.allow)

    assert isinstance(AllowAll(), Policy)
