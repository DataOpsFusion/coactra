from coactra.directory import Seat, Tenant


def test_owner_of_matches_seat_by_domain(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_seat("acme", Seat(tenant_id="acme", role="dba", domain="database"))
    store.add_seat("acme", Seat(tenant_id="acme", role="platform", domain="infrastructure"))

    owner = store.owner_of("acme", "database")
    assert owner is not None and owner.role == "dba"


def test_owner_of_unowned_domain_is_none(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_seat("acme", Seat(tenant_id="acme", role="platform", domain="infrastructure"))
    assert store.owner_of("acme", "billing") is None


def test_owner_of_is_tenant_scoped(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_tenant(Tenant(tenant_id="globex"))
    store.add_seat("globex", Seat(tenant_id="globex", role="dba", domain="database"))
    # acme has no database owner even though globex does.
    assert store.owner_of("acme", "database") is None
