from datetime import UTC, datetime

import pytest

from coactra import Scope
from coactra.memory import Recollection


def test_scope_minimal_tenant_only():
    s = Scope(tenant_id="acme")
    assert s.tenant_id == "acme"
    assert s.namespace == "default"
    assert s.agent_id is None
    assert s.session_id is None


def test_scope_is_frozen_hashable_and_equal():
    a = Scope(tenant_id="acme", agent_id="builder")
    b = Scope(tenant_id="acme", agent_id="builder")
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_scope_rejects_empty_tenant():
    with pytest.raises(ValueError):
        Scope(tenant_id="")


def test_scope_key_puts_tenant_first():
    assert Scope(tenant_id="acme", agent_id="builder", session_id="s1").key == (
        "acme:default:builder:s1"
    )
    assert Scope(tenant_id="acme").key == "acme:default:*:*"
    assert Scope(tenant_id="acme", namespace="company").key == "acme:company:*:*"
    assert (
        Scope(tenant_id="acme", namespace="department/infrastructure").key
        == "acme:department/infrastructure:*:*"
    )


def test_scope_rejects_delimiter_in_fields():
    # ':' is the encoding delimiter; allowing it lets two distinct scopes collapse to
    # the same engine key (cross-tenant collision). Every field must reject it.
    for kwargs in (
        {"tenant_id": "acme:builder"},
        {"tenant_id": "acme", "namespace": "bad:namespace"},
        {"tenant_id": "acme", "agent_id": "a:b"},
        {"tenant_id": "acme", "session_id": "s:1"},
    ):
        with pytest.raises(ValueError, match="reserved"):
            Scope(**kwargs)


def test_scope_rejects_reserved_and_empty_narrowing_fields():
    # '*' is the absent-field placeholder in the encoded key, and an empty agent/session
    # would alias the absent slot — both must be rejected so the key stays injective.
    for kwargs in (
        {"tenant_id": "*"},
        {"tenant_id": "acme", "namespace": "*"},
        {"tenant_id": "acme", "namespace": ""},
        {"tenant_id": "acme", "agent_id": "*"},
        {"tenant_id": "acme", "session_id": "*"},
        {"tenant_id": "acme", "agent_id": ""},
        {"tenant_id": "acme", "session_id": ""},
    ):
        with pytest.raises(ValueError):
            Scope(**kwargs)


def test_scope_key_keeps_namespace_and_agent_dimensions_distinct():
    namespaced = Scope(tenant_id="acme", namespace="company")
    agent = Scope(tenant_id="acme", agent_id="company")
    assert namespaced.key != agent.key


def test_recollection_is_plain_with_defaults():
    r = Recollection(text="hi")
    assert r.text == "hi"
    assert r.score == 0.0
    assert r.source_id == ""
    assert r.when is None
    assert r.metadata == {}


def test_recollection_carries_when_and_metadata():
    now = datetime.now(UTC)
    r = Recollection(text="x", score=0.9, source_id="abc", when=now, metadata={"k": "v"})
    assert r.score == 0.9
    assert r.source_id == "abc"
    assert r.when is now
    assert r.metadata == {"k": "v"}
