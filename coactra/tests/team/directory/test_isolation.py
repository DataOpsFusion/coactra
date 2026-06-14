import pytest

from coactra.team.directory import (
    CrossTenantError,
    Department,
    Member,
    MemberKind,
    Seat,
    Tenant,
)


def _two_tenants(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_tenant(Tenant(tenant_id="globex"))


def test_members_query_never_crosses_tenants(store):
    _two_tenants(store)
    store.add_member("acme", Member(tenant_id="acme", name="alice", kind=MemberKind.agent))
    store.add_member("globex", Member(tenant_id="globex", name="zara", kind=MemberKind.agent))

    assert {m.name for m in store.members("acme")} == {"alice"}
    assert {m.name for m in store.members("globex")} == {"zara"}


def test_entity_tenant_mismatch_raises(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    # A seat carrying tenant_id="globex" added under "acme" is a breach.
    with pytest.raises(CrossTenantError):
        store.add_seat("acme", Seat(tenant_id="globex", role="intruder"))


def test_cross_tenant_assignment_raises(store):
    _two_tenants(store)
    acme_seat = store.add_seat("acme", Seat(tenant_id="acme", role="platform"))
    globex_member = store.add_member(
        "globex", Member(tenant_id="globex", name="zara", kind=MemberKind.agent)
    )
    # Assigning a globex member to an acme seat must NOT silently succeed.
    with pytest.raises(CrossTenantError):
        store.assign("acme", member_id=globex_member.id, seat_id=acme_seat.id)


def test_cross_tenant_reporting_edge_raises(store):
    _two_tenants(store)
    acme_seat = store.add_seat("acme", Seat(tenant_id="acme", role="a"))
    globex_seat = store.add_seat("globex", Seat(tenant_id="globex", role="b"))
    with pytest.raises(CrossTenantError):
        store.reports_to("acme", seat_id=acme_seat.id, reports_to_seat_id=globex_seat.id)


def test_cross_tenant_assignment_department_raises(store):
    _two_tenants(store)
    globex_node = store.add_department("globex", Department(tenant_id="globex", name="Operations"))
    acme_member = store.add_member(
        "acme", Member(tenant_id="acme", name="alice", kind=MemberKind.agent)
    )

    with pytest.raises(CrossTenantError):
        store.assign("acme", member_id=acme_member.id, department_id=globex_node.id)


def test_cross_tenant_place_member_node_raises(store):
    _two_tenants(store)
    globex_node = store.add_department("globex", Department(tenant_id="globex", name="Operations"))
    acme_member = store.add_member(
        "acme", Member(tenant_id="acme", name="alice", kind=MemberKind.agent)
    )

    with pytest.raises(CrossTenantError):
        store.place_member("acme", member_id=acme_member.id, node_id=globex_node.id, seat_id=None)
