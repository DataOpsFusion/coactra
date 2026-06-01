"""The new READ/directory APIs on OrgStore + SqliteOrgStore.

children_of / memberships(recursive) / seat_of / node / roots / directory — so a
consumer reads the whole org through the PUBLIC api, never reaching into _engine.
All tenant-scoped.
"""

from coactra.organization import (
    Department,
    Member,
    MemberKind,
    Seat,
    Tenant,
)


def _seed(store):
    store.add_tenant(Tenant(tenant_id="acme", name="Acme"))
    root = store.add_department("acme", Department(tenant_id="acme", name="Acme"))
    eng = store.add_department(
        "acme", Department(tenant_id="acme", name="Engineering", parent_id=root.id)
    )
    rnd = store.add_department(
        "acme", Department(tenant_id="acme", name="R&D", parent_id=eng.id)
    )
    seat = store.add_seat("acme", Seat(tenant_id="acme", role="lead", permissions=["deploy"]))
    ada = store.add_member("acme", Member(tenant_id="acme", name="ada", kind=MemberKind.human))
    store.assign("acme", member_id=ada.id, seat_id=seat.id, department_id=rnd.id)
    return root, eng, rnd, seat, ada


def test_roots_returns_only_parentless_nodes(store):
    root, eng, rnd, _, _ = _seed(store)
    roots = store.roots("acme")
    assert [n.id for n in roots] == [root.id]


def test_children_of_returns_direct_children(store):
    root, eng, rnd, _, _ = _seed(store)
    assert [c.id for c in store.children_of("acme", root.id)] == [eng.id]
    assert [c.id for c in store.children_of("acme", eng.id)] == [rnd.id]
    assert store.children_of("acme", rnd.id) == []


def test_node_fetches_a_single_node_by_id(store):
    root, _, rnd, _, _ = _seed(store)
    assert store.node("acme", rnd.id).name == "R&D"
    assert store.node("acme", 9999) is None


def test_seat_of_returns_the_members_seat(store):
    _, _, _, seat, ada = _seed(store)
    got = store.seat_of("acme", ada.id)
    assert got is not None and got.id == seat.id and got.role == "lead"


def test_memberships_non_recursive_is_just_that_node(store):
    root, eng, rnd, _, ada = _seed(store)
    # ada sits in rnd, so the eng node alone has no direct members
    assert store.memberships("acme", eng.id, recursive=False) == []
    direct = store.memberships("acme", rnd.id, recursive=False)
    assert [m.id for m in direct] == [ada.id]


def test_memberships_recursive_collects_the_subtree(store):
    root, eng, rnd, _, ada = _seed(store)
    rec = store.memberships("acme", root.id, recursive=True)
    assert [m.name for m in rec] == ["ada"]
    # and from eng down it also finds ada (in rnd)
    assert [m.name for m in store.memberships("acme", eng.id, recursive=True)] == ["ada"]


def test_directory_bulk_join_returns_full_picture(store):
    root, eng, rnd, seat, ada = _seed(store)
    d = store.directory("acme")
    assert {n.name for n in d.nodes} == {"Acme", "Engineering", "R&D"}
    assert {m.name for m in d.members} == {"ada"}
    # seat_by_member maps the member id to its seat
    assert d.seat_by_member[ada.id].role == "lead"
    # node_by_member places ada in R&D
    assert d.node_by_member[ada.id] == rnd.id


def test_directory_is_tenant_scoped(store):
    _seed(store)
    store.add_tenant(Tenant(tenant_id="globex", name="Globex"))
    store.add_department("globex", Department(tenant_id="globex", name="Globex"))
    d = store.directory("acme")
    assert all(n.tenant_id == "acme" for n in d.nodes)
    assert store.roots("globex") and store.roots("globex")[0].name == "Globex"
