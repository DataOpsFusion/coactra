from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from coactra.memory import Recollection, Scope


def test_scope_minimal_tenant_only():
    s = Scope(tenant="acme")
    assert s.tenant == "acme"
    assert s.namespace is None
    assert s.agent is None
    assert s.session is None


def test_scope_is_frozen_hashable_and_equal():
    a = Scope(tenant="acme", agent="builder")
    b = Scope(tenant="acme", agent="builder")
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_scope_rejects_empty_tenant():
    with pytest.raises(ValidationError):
        Scope(tenant="")


def test_scope_key_puts_tenant_first():
    assert Scope(tenant="acme", agent="builder", session="s1").key == "acme:builder:s1"
    assert Scope(tenant="acme").key == "acme:*:*"
    assert Scope(tenant="acme", namespace="company").key == "acme:@:company:*:*"
    assert (
        Scope(tenant="acme", namespace="department/infrastructure").key
        == "acme:@:department/infrastructure:*:*"
    )


def test_scope_rejects_delimiter_in_fields():
    # ':' is the encoding delimiter; allowing it lets two distinct scopes collapse to
    # the same engine key (cross-tenant collision). Every field must reject it.
    for kwargs in (
        {"tenant": "acme:builder"},
        {"tenant": "acme", "namespace": "bad:namespace"},
        {"tenant": "acme", "agent": "a:b"},
        {"tenant": "acme", "session": "s:1"},
    ):
        with pytest.raises(ValidationError, match="':'"):
            Scope(**kwargs)


def test_scope_rejects_reserved_and_empty_narrowing_fields():
    # '*' is the absent-field placeholder in the encoded key, and an empty agent/session
    # would alias the absent slot — both must be rejected so the key stays injective.
    for kwargs in (
        {"tenant": "*"},
        {"tenant": "acme", "namespace": "*"},
        {"tenant": "acme", "namespace": ""},
        {"tenant": "acme", "agent": "*"},
        {"tenant": "acme", "session": "*"},
        {"tenant": "acme", "agent": ""},
        {"tenant": "acme", "session": ""},
    ):
        with pytest.raises(ValidationError):
            Scope(**kwargs)


def test_namespaced_scope_never_collides_with_legacy_scope():
    namespaced = Scope(tenant="acme", namespace="company")
    legacy = Scope(tenant="acme", agent="@")
    assert namespaced.key != legacy.key


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
