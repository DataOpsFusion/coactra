from coactra.organization import Member, MemberKind, Seat, Tenant


def test_flat_fleet_create_member_with_seat(store):
    store.add_tenant(Tenant(tenant_id="acme", name="Acme"))
    seat = store.add_seat("acme", Seat(tenant_id="acme", role="platform"))
    member = store.add_member("acme", Member(tenant_id="acme", name="alice", kind=MemberKind.agent))
    store.assign("acme", member_id=member.id, seat_id=seat.id)  # no department => flat

    listed = store.members("acme")
    assert [m.name for m in listed] == ["alice"]
    assert seat.id is not None and member.id is not None


def test_add_seat_persists_role_and_domain(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    seat = store.add_seat("acme", Seat(tenant_id="acme", role="dba", domain="database"))
    assert seat.role == "dba"
    assert seat.domain == "database"
