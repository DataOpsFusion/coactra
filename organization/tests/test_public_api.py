import fleetlib.organization as org


def test_public_surface_is_complete():
    expected = {
        "__version__",
        "MemberKind",
        "Tenant",
        "Department",
        "Seat",
        "Member",
        "Membership",
        "ReportingEdge",
        "EscalationRoute",
        "PolicyRef",
        "OrgStore",
        "SqliteOrgStore",
        "CrossTenantError",
        "make_engine",
    }
    assert expected <= set(org.__all__)
    for name in expected:
        assert hasattr(org, name), name


def test_default_store_satisfies_protocol():
    assert isinstance(org.SqliteOrgStore(), org.OrgStore)


def test_end_to_end_directory_walkthrough():
    store = org.SqliteOrgStore()
    store.add_tenant(org.Tenant(tenant_id="acme", name="Acme"))

    platform = store.add_seat("acme", org.Seat(tenant_id="acme", role="platform", domain="infrastructure"))
    manager = store.add_seat("acme", org.Seat(tenant_id="acme", role="manager"))
    store.reports_to("acme", platform.id, manager.id)

    alice = store.add_member("acme", org.Member(tenant_id="acme", name="alice", kind=org.MemberKind.agent))
    store.assign("acme", member_id=alice.id, seat_id=platform.id)

    # who owns this?
    assert store.owner_of("acme", "infrastructure").role == "platform"
    # where does escalation go?
    assert store.escalate("acme", platform.id).id == manager.id
    # flat-fleet listing
    assert [m.name for m in store.members("acme")] == ["alice"]
