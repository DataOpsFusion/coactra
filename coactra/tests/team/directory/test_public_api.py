import coactra.team.directory as org


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

    platform = store.add_seat(
        "acme", org.Seat(tenant_id="acme", role="platform", domain="infrastructure")
    )
    manager = store.add_seat("acme", org.Seat(tenant_id="acme", role="manager"))
    store.reports_to("acme", platform.id, manager.id)

    alice = store.add_member(
        "acme", org.Member(tenant_id="acme", name="alice", kind=org.MemberKind.agent)
    )
    store.assign("acme", member_id=alice.id, seat_id=platform.id)

    # who owns this?
    assert store.owner_of("acme", "infrastructure").role == "platform"
    # where does escalation go?
    assert store.escalate("acme", platform.id).id == manager.id
    # flat-fleet listing
    assert [m.name for m in store.members("acme")] == ["alice"]


def test_v2_domain_surface_is_exported():
    expected = {
        "Organization",
        "make_org_store",
        "load_org",
        "save_org",
        "Directory",
        "Action",
        "Effect",
        "PermissionSet",
        "MissingExtraError",
    }
    assert expected <= set(org.__all__)
    for name in expected:
        assert hasattr(org, name), name


def test_domain_walkthrough_matches_the_design_example():
    # The illustrative DESIGN.md API, exercised end to end through the public surface.
    store = org.make_org_store("sqlite://")
    acme = org.Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    rnd = eng.add_child("R&D")

    ada = rnd.hire(name="ada", kind="human", role="lead", permissions={"deploy", "approve"})
    rnd.grant("deploy")

    assert rnd.can(ada, "deploy") is True
    assert acme.can(ada, "deploy") is True  # resolves through the tree, node-independent
    assert ada.dn == "acme/Engineering/R&D/ada"
    assert rnd.manager is eng

    rnd.suspend(ada)
    assert rnd.can(ada, "deploy") is False

    rnd.move(ada, to=eng)
    assert ada.dn == "acme/Engineering/ada"
    rnd.unsuspend(ada)

    org.save_org(acme, store=store)
    again = org.load_org("acme", store=store)
    assert again is not None
    reloaded_ada = {m.name: m for m in again.members(recursive=True)}["ada"]
    assert again.can(reloaded_ada, "deploy") is True
