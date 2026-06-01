from coactra.organization import Department, Seat, Tenant


def _two_seats(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    junior = store.add_seat("acme", Seat(tenant_id="acme", role="platform"))
    senior = store.add_seat("acme", Seat(tenant_id="acme", role="manager"))
    return junior, senior


def test_reports_to_records_an_edge(store):
    junior, senior = _two_seats(store)
    store.reports_to("acme", seat_id=junior.id, reports_to_seat_id=senior.id)
    # The edge is queryable as the manager of the junior seat.
    assert store.manager_of("acme", junior.id).id == senior.id


def test_seat_without_edge_has_no_manager(store):
    junior, _ = _two_seats(store)
    # Flat fleet: a seat may simply have no one above it.
    assert store.manager_of("acme", junior.id) is None


def test_department_can_be_created_and_used_in_assignment(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    seat = store.add_seat("acme", Seat(tenant_id="acme", role="rnd"))
    from coactra.organization import Member, MemberKind

    member = store.add_member("acme", Member(tenant_id="acme", name="bob", kind=MemberKind.agent))
    dept = store.add_department("acme", Department(tenant_id="acme", name="R&D"))
    store.assign("acme", member_id=member.id, seat_id=seat.id, department_id=dept.id)
    assert dept.id is not None
