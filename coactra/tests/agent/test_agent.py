import asyncio

import pytest

from coactra.agent import (
    AgentRef,
    CollaborationDenied,
    DelegationGrant,
    Scope,
    make_agent,
)
from coactra.agent.ports import FakeMemory, FakeWorkspace


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
        self.sent.append((dst.tenant_id, dst.agent_id, question))
        return f"{dst.agent_id}:ack"


ACME = Scope(tenant_id="acme", namespace="agent:platform")


def _agent(**kw):
    return make_agent(scope=ACME, **kw)


def test_make_agent_derives_me_from_namespace_and_wires_defaults():
    a = _agent()
    assert a.scope == ACME
    assert a.me == "agent:platform"  # derived from scope.namespace


def test_make_agent_me_override():
    a = make_agent(scope=ACME, me="agent:custom")
    assert a.me == "agent:custom"


def test_mount_mcp_is_not_visible_until_begin_turn():
    a = _agent()
    a.mount_mcp("fs", FakeServer(["read_file"]), effective="next_turn")
    assert a.tools() == []  # staged, not yet exposed
    a.begin_turn()
    assert {t.qualified_name for t in a.tools_specs()} == {"fs.read_file"}
    assert a.tools() == ["fs.read_file"]


def test_mcp_kwarg_stages_initial_mounts_invisible_until_begin_turn():
    a = make_agent(scope=ACME, mcp={"fs": FakeServer(["read_file", "write_file"])})
    assert a.tools() == []  # staged at construction but invisible
    a.begin_turn()
    assert set(a.tools()) == {"fs.read_file", "fs.write_file"}
    assert set(a.tools_of("fs")) == {"fs.read_file", "fs.write_file"}


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
    assert a.can_talk("agent:security") is True
    assert a.talk("agent:security", "is it safe?") == "agent:security:ack"


def test_denied_talk_raises():
    class DenyAll:
        def can_talk(self, src, dst, scope):
            return False

    a = _agent(transport=FakeTransport(), policy=DenyAll())
    assert a.can_talk("agent:security") is False
    with pytest.raises(CollaborationDenied):
        a.talk("agent:security", "hi")


def test_cross_tenant_talk_denied_through_the_agent_facade():
    t = FakeTransport()
    a = _agent(transport=t)
    with pytest.raises(CollaborationDenied):
        a.talk(AgentRef(tenant_id="globex", agent_id="agent:x"), "hi")
    assert t.sent == []  # gated before the wire


def test_agent_memory_is_async_and_scoped():
    a = _agent()

    async def scenario():
        await a.remember(["the deploy passed"])
        return await a.recall("deploy")

    hits = asyncio.run(scenario())
    assert [r["text"] for r in hits] == ["the deploy passed"]


def test_agent_delegates_run_procedure_to_the_port():
    a = _agent()
    out = a.run_procedure("deploy", {"host": "web1"})
    assert out == {"procedure": "deploy", "state": {"host": "web1"}, "ran": True}


def test_think_forwards_to_ai_port():
    a = _agent()
    assert a.think("hello") == "completion:hello"


def test_workspace_scope_isolation_via_shared_port_type():
    a = _agent()
    a.workspace_write("notes.md", "hello")
    assert a.workspace_read("notes.md") == "hello"
    # a different agent with its OWN workspace cannot see it
    other = make_agent(scope=Scope(tenant_id="globex"), workspace=FakeWorkspace())
    assert other.workspace_read("notes.md") == ""


def test_injected_port_is_the_one_called():
    # DI proof: the agent calls the injected memory, not a fresh default.
    injected = FakeMemory()
    a = _agent(memory=injected)

    async def scenario():
        await a.remember(["x marks the spot"])

    asyncio.run(scenario())
    # the data landed in the INJECTED instance's store, keyed by scope
    assert injected._store[ACME.key] == ["x marks the spot"]
