import pytest

from fleetlib.agent import (
    Agent,
    CollaborationDenied,
    DelegationGrant,
    Scope,
)


class FakeServer:
    def __init__(self, names):
        self._names = list(names)

    def list_tools(self):
        return list(self._names)


class FakeTransport:
    """A2ATransportPort fake — the target is a tenant-qualified AgentRef."""

    def __init__(self):
        self.sent = []

    def send(self, dst, question, scope):
        self.sent.append(dst.agent_id)
        return f"{dst.agent_id}:ack"


ACME = Scope(tenant_id="acme", namespace="agent:platform")


def _agent(**kw):
    base = dict(scope=ACME, me="agent:platform")
    base.update(kw)
    return Agent(**base)


def test_agent_has_scope_and_default_ports():
    a = _agent()
    assert a.scope == ACME
    # default fakes are wired in so the agent works out of the box
    a.memory("the deploy passed")
    assert a.recall("deploy") == ["the deploy passed"]


def test_mount_mcp_is_not_visible_until_begin_turn():
    a = _agent()
    a.mount_mcp("fs", FakeServer(["read_file"]), effective="next_turn")
    assert a.tools() == []  # staged, not yet exposed
    a.begin_turn()
    assert {t.qualified_name for t in a.tools_specs()} == {"fs.read_file"}
    assert a.tools() == ["fs.read_file"]


def test_act_on_behalf_of_exchanges_without_passthrough():
    a = _agent()
    identity = a.act_on_behalf_of(
        DelegationGrant(subject_token="HUMAN-SECRET", actor="agent:platform")
    )
    assert identity.token != "HUMAN-SECRET"
    assert "HUMAN-SECRET" not in identity.token
    assert identity.tenant_id == "acme"


def test_delegate_further_extends_the_actor_chain_through_the_protocol():
    a = _agent()
    first = a.act_on_behalf_of(
        DelegationGrant(subject_token="HUMAN-SECRET", actor="agent:platform")
    )
    second = a.delegate_further(first, actor="agent:security")
    assert second.act_chain == ["agent:platform", "agent:security"]
    assert "HUMAN-SECRET" not in second.token


def test_can_talk_uses_the_collaboration_policy():
    a = _agent(transport=FakeTransport())
    # default policy (AllowSameTenant, no allow-set) permits intra-tenant talk
    assert a.can_talk("agent:security") is True
    reply = a.ask("agent:security", "is it safe?")
    assert reply == "agent:security:ack"


def test_denied_talk_raises():
    class DenyAll:
        def can_talk(self, src, dst, scope):
            return False

    a = _agent(transport=FakeTransport(), collaboration_policy=DenyAll())
    assert a.can_talk("agent:security") is False
    with pytest.raises(CollaborationDenied):
        a.ask("agent:security", "hi")


def test_agent_delegates_run_workflow_to_the_port():
    a = _agent()
    out = a.run_procedure("deploy")
    assert out == {"procedure": "deploy", "tenant": "acme", "ran": True}


def test_scope_threads_into_every_subsystem():
    a = _agent()
    a.workspace_write("notes.md", "hello")
    assert a.workspace_read("notes.md") == "hello"
    # a different-tenant agent cannot see it (isolation through the same fake store type)
    other = Agent(scope=Scope(tenant_id="globex"), me="x", workspace=a._workspace)
    assert other.workspace_read("notes.md") == ""
