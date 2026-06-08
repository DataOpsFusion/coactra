from coactra.team.directory import Organization, load_org, make_org_store, save_org


def test_domain_roundtrip_preserves_reporting_routes_policy_ownership_and_member_audit():
    store = make_org_store("sqlite://")
    acme = Organization.root(tenant="acme", name="Acme")
    team = acme.add_child("Platform")
    engineer = team.hire(
        "ada", role="engineer", seniority=7, created_by="human:ops", approved_by="human:cto"
    )
    manager = team.hire("lin", role="manager")
    engineer.seat.domain = "database"
    acme.reports_to(engineer.seat, manager.seat)
    acme.route_escalation(engineer.seat, manager.seat)
    acme.add_policy_ref("retention", version=2, target="logs")

    save_org(acme, store=store)
    again = load_org("acme", store=store)

    ada = {member.name: member for member in again.members(recursive=True)}["ada"]
    assert ada.seniority == 7
    assert ada.created_by == "human:ops"
    assert ada.approved_by == "human:cto"
    assert again.owner_of("database").role == "engineer"
    assert [(a.role, b.role) for a, b in again.reporting_edges] == [("engineer", "manager")]
    assert [(a.role, b.role) for a, b in again.escalation_routes] == [("engineer", "manager")]
    assert [(ref.name, ref.version, ref.target) for ref in again.policy_refs] == [
        ("retention", 2, "logs")
    ]


def test_domain_resave_reconciles_archived_status_and_audit_fields():
    store = make_org_store("sqlite://")
    acme = Organization.root(tenant="acme", name="Acme")
    ada = acme.hire("ada", seniority=1, created_by="human:ops")
    save_org(acme, store=store)
    ada.seniority = 9
    ada.approved_by = "human:cto"
    acme.archive(ada)
    save_org(acme, store=store)

    again = load_org("acme", store=store)
    reloaded = again.members(recursive=True)[0]
    assert reloaded.status == "archived"
    assert reloaded.seniority == 9
    assert reloaded.approved_by == "human:cto"
