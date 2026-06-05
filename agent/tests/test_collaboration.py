import asyncio

import pytest

from coactra.agent import (
    A2ATransportPort,
    AgentRef,
    AllowSameTenant,
    AsyncA2ATransportPort,
    AsyncPolicyGatedCollaborator,
    CollaborationDenied,
    CollaborationPolicy,
    PolicyGatedCollaborator,
    Scope,
)


class AsyncFakeTransport:
    def __init__(self):
        self.sent = []

    async def send(self, dst, question, scope):
        self.sent.append((dst.agent_id, question, dst.tenant_id))
        return f"{dst.agent_id}:ack"


class FakeTransport:
    """In-process A2ATransportPort: echoes a canned reply, records who was asked.

    The target is TENANT-QUALIFIED — `dst` is an AgentRef carrying its own tenant. The
    transport records (agent_id, question, tenant_id) and replies off the agent_id so the
    existing reply-string assertions stay readable.
    """

    def __init__(self):
        self.sent = []

    def send(self, dst, question, scope):
        self.sent.append((dst.agent_id, question, dst.tenant_id))
        return f"{dst.agent_id}:ack"


ACME = Scope(tenant_id="acme")


def test_defaults_satisfy_protocols():
    assert isinstance(AllowSameTenant(), CollaborationPolicy)
    assert isinstance(FakeTransport(), A2ATransportPort)
    assert isinstance(AsyncFakeTransport(), AsyncA2ATransportPort)


def test_allow_same_tenant_permits_intra_tenant_talk():
    p = AllowSameTenant()
    assert p.can_talk("agent:a", "agent:b", ACME) is True


def test_policy_gated_collaborator_sends_when_allowed():
    t = FakeTransport()
    c = PolicyGatedCollaborator(transport=t, policy=AllowSameTenant(), scope=ACME, me="agent:a")
    reply = c.ask("agent:b", "is it safe?", {})
    assert reply == "agent:b:ack"
    assert t.sent == [("agent:b", "is it safe?", "acme")]


def test_denied_talk_raises_and_never_hits_the_wire():
    class DenyAll:
        def can_talk(self, src, dst, scope):
            return False

    t = FakeTransport()
    c = PolicyGatedCollaborator(transport=t, policy=DenyAll(), scope=ACME, me="agent:a")
    with pytest.raises(CollaborationDenied):
        c.ask("agent:b", "hi", {})
    assert t.sent == []  # policy gates BEFORE the transport


def test_allow_set_narrows_who_may_talk_to_whom():
    # AllowSameTenant gates the WHO-MAY-TALK-TO-WHOM pair WITHIN a tenant. With no allow-set
    # it permits any intra-tenant pair (open default); given an allow-set it restricts to
    # listed (src_agent_id, dst_agent_id) pairs.
    policy = AllowSameTenant(allowed={("agent:a", "agent:b")})
    assert policy.can_talk("agent:a", "agent:b", ACME) is True
    assert policy.can_talk("agent:a", "agent:c", ACME) is False  # not in the allow-set


# --- tenant-qualified, DENIABLE cross-tenant targets (design override) -----------------


def test_agent_ref_is_tenant_qualified():
    ref = AgentRef(tenant_id="acme", agent_id="agent:a")
    assert ref.tenant_id == "acme"
    assert ref.agent_id == "agent:a"


def test_cross_tenant_talk_is_denied():
    # A tenant-qualified target whose tenant differs from the source's is DENIED — the
    # genuine cross-tenant boundary the AgentRef makes expressible. This is NOT vacuous:
    # both refs are constructed, the tenants genuinely differ, and the policy returns False.
    acme_a = AgentRef(tenant_id="acme", agent_id="agent:a")
    globex_b = AgentRef(tenant_id="globex", agent_id="agent:b")
    assert AllowSameTenant().can_talk(acme_a, globex_b, ACME) is False
    # ...and the same pair WITHIN one tenant is permitted, proving the denial is the
    # tenant difference, not the agent ids.
    globex_scope = Scope(tenant_id="globex")
    globex_a = AgentRef(tenant_id="globex", agent_id="agent:a")
    assert AllowSameTenant().can_talk(globex_a, globex_b, globex_scope) is True


def test_cross_tenant_ask_never_hits_the_wire():
    # End-to-end: a cross-tenant AgentRef target is gated BEFORE the transport, so the wire
    # is never touched even though a real transport is wired in.
    t = FakeTransport()
    c = PolicyGatedCollaborator(transport=t, policy=AllowSameTenant(), scope=ACME, me="agent:a")
    globex_b = AgentRef(tenant_id="globex", agent_id="agent:b")
    with pytest.raises(CollaborationDenied):
        c.ask(globex_b, "hi", {})
    assert t.sent == []


def test_collaborator_satisfies_workflows_collaborator_shape():
    # The concrete inter-lib seam: workflow's `ask` step calls a Collaborator with
    # .ask(agent, question, state). PolicyGatedCollaborator structurally matches it, so it
    # drops straight into a coactra.jobs.workflow RunContext without an adapter.
    c = PolicyGatedCollaborator(
        transport=FakeTransport(), policy=AllowSameTenant(), scope=ACME, me="agent:a"
    )
    assert hasattr(c, "ask")
    answer = c.ask("agent:b", "q", {"state": 1})
    assert answer == "agent:b:ack"


def test_collaborator_satisfies_workflows_escalation_router_shape():
    # workflow's EscalationRouter is .route(escalation, chain) -> decider id.
    c = PolicyGatedCollaborator(
        transport=FakeTransport(), policy=AllowSameTenant(), scope=ACME, me="agent:a"
    )

    class Esc:
        reason = "stuck"

    assert c.route(Esc(), chain=["manager", "human"]) == "human"


def test_async_policy_gated_collaborator_sends_when_allowed():
    t = AsyncFakeTransport()
    c = AsyncPolicyGatedCollaborator(
        transport=t, policy=AllowSameTenant(), scope=ACME, me="agent:a"
    )
    reply = asyncio.run(c.ask("agent:b", "is it safe?", {}))
    assert reply == "agent:b:ack"
    assert t.sent == [("agent:b", "is it safe?", "acme")]


def test_async_cross_tenant_ask_never_hits_the_wire():
    t = AsyncFakeTransport()
    c = AsyncPolicyGatedCollaborator(
        transport=t, policy=AllowSameTenant(), scope=ACME, me="agent:a"
    )
    with pytest.raises(CollaborationDenied):
        asyncio.run(c.ask(AgentRef(tenant_id="globex", agent_id="agent:b"), "hi", {}))
    assert t.sent == []
