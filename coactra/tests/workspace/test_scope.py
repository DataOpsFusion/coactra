import pytest
from pydantic import ValidationError

from coactra.workspace import Scope


def test_scope_fields():
    s = Scope(tenant_id="acme", agent_id="planner")
    assert s.tenant_id == "acme"
    assert s.agent_id == "planner"


def test_scope_is_hashable_and_equal():
    a = Scope(tenant_id="acme", agent_id="planner")
    b = Scope(tenant_id="acme", agent_id="planner")
    assert a == b
    assert hash(a) == hash(b)
    assert {a, b} == {a}


def test_scope_rejects_empty_parts():
    with pytest.raises(ValidationError):
        Scope(tenant_id="", agent_id="planner")
    with pytest.raises(ValidationError):
        Scope(tenant_id="acme", agent_id="")


def test_scope_key_is_stable_relative_path():
    assert Scope(tenant_id="acme", agent_id="planner").key == "acme/planner"


@pytest.mark.parametrize("part", ["..", ".", "../globex", "acme/other", r"acme\other"])
def test_scope_rejects_path_components_that_can_escape_the_desk(part):
    with pytest.raises(ValidationError):
        Scope(tenant_id=part, agent_id="planner")
