import pytest

from coactra.scope import Scope, is_safe_path_component


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
    with pytest.raises(ValueError):
        Scope(tenant_id="", agent_id="planner")
    with pytest.raises(ValueError):
        Scope(tenant_id="acme", agent_id="")


def test_scope_key_is_stable_relative_path():
    assert Scope(tenant_id="acme", agent_id="planner").key == "acme:default:planner:*"


@pytest.mark.parametrize("part", ["..", ".", "../globex", "acme/other", r"acme\other"])
def test_path_safety_is_a_workspace_boundary_rule(part):
    assert not is_safe_path_component(part)


def test_core_scope_allows_namespace_paths():
    assert Scope(tenant_id="acme", namespace="department/engineering").namespace == (
        "department/engineering"
    )
