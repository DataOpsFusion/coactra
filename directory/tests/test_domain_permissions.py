"""Permission resolution — AD-style inheritance, block_inheritance, member overrides.

In-memory only. Pins the exact algorithm from DESIGN.md:
  can(member, action) walks member-node -> root (stopping at block_inheritance),
  member override wins outright (deny beats allow), else union of role/seat perms
  and node grants on the path. Suspended => no access. Cross-tenant => raises.
"""

import pytest

from coactra.directory import CrossTenantError, Organization


def _tree():
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    rnd = eng.add_child("R&D")
    return acme, eng, rnd


def test_role_seat_permission_grants_without_any_node_grant():
    _, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="human", role="lead", permissions={"deploy", "approve"})
    assert rnd.can(ada, "deploy") is True
    assert rnd.can(ada, "approve") is True
    assert rnd.can(ada, "delete-tenant") is False


def test_node_grant_inherits_down_to_member():
    acme, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="human", role="ic")
    acme.grant("read-logs")  # granted high in the tree
    assert rnd.can(ada, "read-logs") is True  # inherited down


def test_grant_on_members_own_node_applies():
    _, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="agent")
    rnd.grant("deploy")
    assert rnd.can(ada, "deploy") is True


def test_can_is_node_independent_resolves_off_members_node():
    acme, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="agent", role="lead", permissions={"deploy"})
    # Called from the root or from R&D, the answer is the same — it keys off ada's node.
    assert acme.can(ada, "deploy") == rnd.can(ada, "deploy") == True  # noqa: E712


def test_block_inheritance_excludes_ancestor_grants_above_the_block():
    acme, eng, rnd = _tree()
    ada = rnd.hire(name="ada", kind="agent")
    acme.grant("root-grant")          # above the block
    eng.grant("eng-grant")            # AT the block node
    rnd.grant("rnd-grant")            # below the block
    eng.block_inheritance = True      # block at Engineering

    assert rnd.can(ada, "rnd-grant") is True    # below the block — kept
    assert rnd.can(ada, "eng-grant") is True    # AT the block node — kept
    assert rnd.can(ada, "root-grant") is False  # above the block — excluded


def test_member_override_deny_beats_a_node_grant():
    acme, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="human", role="lead", permissions={"deploy"})
    acme.grant("deploy")
    ada.deny("deploy")  # explicit deny wins over role perm AND node grant
    assert rnd.can(ada, "deploy") is False


def test_member_override_allow_wins_with_no_node_grant():
    _, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="agent")  # no role, no node grant
    ada.allow("approve")
    assert rnd.can(ada, "approve") is True


def test_suspended_member_can_do_nothing_even_with_grants():
    acme, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="human", role="lead", permissions={"deploy"})
    acme.grant("deploy")
    rnd.suspend(ada)
    assert rnd.can(ada, "deploy") is False
    rnd.unsuspend(ada)
    assert rnd.can(ada, "deploy") is True


def test_can_across_tenants_raises():
    acme, _, rnd = _tree()
    ada = rnd.hire(name="ada", kind="agent", role="lead", permissions={"deploy"})
    globex = Organization.root(tenant="globex", name="Globex")
    with pytest.raises(CrossTenantError):
        globex.can(ada, "deploy")
