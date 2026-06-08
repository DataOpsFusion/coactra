"""Service layer — save_org / load_org round-trip through an injected store.

The aggregate never instantiates a store; the store is injected. save_org persists the
in-memory tree; load_org rebuilds an equivalent Organization from the store. The
round-trip must preserve: node tree, block_inheritance, node grants, members, seats,
member status, and per-member overrides — proven by replaying can() on the rebuilt tree.
"""

from coactra.team.directory import (
    Organization,
    load_org,
    make_org_store,
    save_org,
)


def _build():
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    rnd = eng.add_child("R&D")
    rnd.grant("deploy")
    eng.block_inheritance = True
    acme.grant("root-only")
    ada = rnd.hire(name="ada", kind="human", role="lead", permissions={"approve"})
    sleepy = rnd.hire(name="sleepy", kind="agent")
    rnd.suspend(sleepy)
    ada.deny("approve")  # explicit deny override survives the round-trip
    bob = eng.hire(name="bob", kind="service")
    bob.allow("read")
    return acme, ada, sleepy, bob


def test_save_then_load_rebuilds_the_tree_shape():
    store = make_org_store("sqlite://")
    acme, *_ = _build()
    save_org(acme, store=store)

    again = load_org("acme", store=store)
    assert again.tenant == "acme"
    assert [c.name for c in again.children] == ["Engineering"]
    eng = again.children[0]
    assert [c.name for c in eng.children] == ["R&D"]
    assert eng.block_inheritance is True


def test_round_trip_preserves_members_and_seats():
    store = make_org_store("sqlite://")
    acme, *_ = _build()
    save_org(acme, store=store)
    again = load_org("acme", store=store)

    by_name = {m.name: m for m in again.members(recursive=True)}
    assert set(by_name) == {"ada", "sleepy", "bob"}
    assert by_name["ada"].seat.role == "lead"
    assert by_name["ada"].seat.permissions == {"approve"}
    assert by_name["ada"].dn == "acme/Engineering/R&D/ada"


def test_round_trip_preserves_permission_resolution():
    store = make_org_store("sqlite://")
    acme, *_ = _build()
    save_org(acme, store=store)
    again = load_org("acme", store=store)

    by_name = {m.name: m for m in again.members(recursive=True)}
    ada, sleepy, bob = by_name["ada"], by_name["sleepy"], by_name["bob"]

    # node grant on R&D inherits to ada
    assert again.can(ada, "deploy") is True
    # explicit deny override survived -> approve denied despite the role perm
    assert again.can(ada, "approve") is False
    # block_inheritance at Engineering hides the root-only grant from ada (below it)
    assert again.can(ada, "root-only") is False
    # suspended member can do nothing
    assert again.can(sleepy, "deploy") is False
    # allow override survived
    assert again.can(bob, "read") is True


def test_save_is_idempotent_no_duplicate_on_resave():
    store = make_org_store("sqlite://")
    acme, *_ = _build()
    save_org(acme, store=store)
    save_org(acme, store=store)  # second save must not duplicate
    again = load_org("acme", store=store)
    assert len(again.members(recursive=True)) == 3
    assert len(again.children) == 1


def test_seatless_member_is_placed_and_resolvable_on_reload():
    # A principal hired with no role still has a node placement that survives save/load,
    # and inherits node grants from its node.
    store = make_org_store("sqlite://")
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    eng.hire(name="deployer", kind="service")  # no role
    eng.grant("read")
    save_org(acme, store=store)

    again = load_org("acme", store=store)
    reloaded = {m.name: m for m in again.members(recursive=True)}["deployer"]
    assert reloaded.seat is None
    assert reloaded.dn == "acme/Engineering/deployer"
    assert again.can(reloaded, "read") is True  # inherited from its node


def test_incremental_resave_adds_new_members_and_grants():
    store = make_org_store("sqlite://")
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    eng.hire(name="ada", kind="human", role="lead", permissions={"deploy"})
    save_org(acme, store=store)

    # mutate the same in-memory tree, then re-save
    eng.hire(name="bob", kind="agent")
    eng.grant("read")
    save_org(acme, store=store)

    again = load_org("acme", store=store)
    reloaded = {m.name: m for m in again.members(recursive=True)}
    assert set(reloaded) == {"ada", "bob"}  # no duplicates, bob added
    assert again.can(reloaded["bob"], "read") is True  # the later grant persisted


def test_resave_flushes_mutations_status_block_grant_move_override():
    # The spec contract: mutate in memory, save again, the changes flush.
    store = make_org_store("sqlite://")
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    rnd = eng.add_child("R&D")
    acme.grant("root-grant")
    ada = rnd.hire(name="ada", kind="human", role="lead", permissions={"deploy"})
    ada.allow("legacy")
    save_org(acme, store=store)

    # now mutate the persisted tree and re-save
    rnd.suspend(ada)  # status change
    eng.block_inheritance = True  # block flag change
    acme.revoke("root-grant")  # grant removal
    rnd.grant("rnd-grant")  # grant addition
    rnd.move(ada, to=eng)  # reparent
    del ada.overrides["legacy"]  # override removal
    ada.deny("danger")  # override addition
    save_org(acme, store=store)

    again = load_org("acme", store=store)
    a = {m.name: m for m in again.members(recursive=True)}["ada"]
    reng = again.children[0]
    rrnd = reng.children[0]
    assert a.dn == "acme/Engineering/ada"  # moved
    assert a.status.value == "suspended"  # status flushed
    assert reng.block_inheritance is True  # block flushed
    assert "root-grant" not in again.grants  # revoke flushed
    assert "rnd-grant" in rrnd.grants  # grant-add flushed
    assert a.overrides.get("legacy") is None  # override removed
    assert a.overrides.get("danger").value == "deny"  # override added

    # no duplicate placement rows after move (one seat, one node)
    assert len(again.members(recursive=True)) == 1


def test_hire_keeps_permissions_even_without_a_role():
    acme = Organization.root(tenant="acme", name="Acme")
    svc = acme.hire(name="bot", kind="service", permissions={"deploy"})
    assert svc.seat is not None
    assert svc.seat.permissions == {"deploy"}
    assert acme.can(svc, "deploy") is True


def test_load_unknown_tenant_returns_none():
    store = make_org_store("sqlite://")
    assert load_org("nobody", store=store) is None
