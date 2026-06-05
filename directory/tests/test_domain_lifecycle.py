"""Member lifecycle: remove, move (reparent), recursive listing — in-memory."""

import pytest

from coactra.directory import CrossTenantError, Organization


def _tree():
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    rnd = eng.add_child("R&D")
    return acme, eng, rnd


def test_remove_deletes_the_principal():
    _, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="agent")
    rnd.remove(ada)
    assert rnd.members() == []
    assert ada.node is None


def test_move_reparents_the_principal_and_updates_dn():
    _, eng, rnd = _tree()
    ada = rnd.hire(name="ada", kind="agent")
    assert ada.dn == "acme/Engineering/R&D/ada"
    rnd.move(ada, to=eng)
    assert ada.node is eng
    assert rnd.members() == []
    assert eng.members() == [ada]
    assert ada.dn == "acme/Engineering/ada"


def test_move_into_another_tenant_raises():
    _, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="agent")
    other = Organization.root(tenant="globex", name="Globex")
    with pytest.raises(CrossTenantError):
        rnd.move(ada, to=other)


def test_members_recursive_collects_subtree():
    acme, eng, rnd = _tree()
    a = acme.hire(name="ceo", kind="human")
    b = eng.hire(name="vp", kind="human")
    c = rnd.hire(name="ada", kind="agent")
    # non-recursive: just this node
    assert acme.members() == [a]
    # recursive: this node plus all descendants
    assert {m.name for m in acme.members(recursive=True)} == {"ceo", "vp", "ada"}
    assert {m.name for m in eng.members(recursive=True)} == {"vp", "ada"}
    assert [m.name for m in rnd.members(recursive=True)] == ["ada"]
    assert {a, b, c}  # silence unused


def test_remove_member_not_in_tree_raises():
    _, _, rnd = _tree()
    stray = Organization.root(tenant="acme", name="Other").hire(name="x", kind="agent")
    with pytest.raises(ValueError):
        rnd.remove(stray)
