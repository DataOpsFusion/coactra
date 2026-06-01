import pytest
from pydantic import ValidationError

from fleetlib.agent import Scope


def test_scope_default_namespace():
    s = Scope(tenant_id="acme")
    assert s.tenant_id == "acme"
    assert s.namespace == "default"


def test_scope_is_hashable_and_equal():
    a = Scope(tenant_id="acme", namespace="agent:1")
    b = Scope(tenant_id="acme", namespace="agent:1")
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_scope_rejects_empty_tenant():
    with pytest.raises(ValidationError):
        Scope(tenant_id="")


def test_scope_key_is_stable_string():
    assert Scope(tenant_id="acme", namespace="agent:1").key == "acme/agent:1"
