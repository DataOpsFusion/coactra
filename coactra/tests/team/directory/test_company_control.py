import pytest

from coactra.team.directory import (
    AgentSpec,
    CompanySpec,
    DepartmentSpec,
    RoleSpec,
    SeniorityLevelSpec,
    bootstrap_company,
    load_org,
    make_org_store,
    preview_company,
    seniority_rank,
)


def _spec() -> CompanySpec:
    return CompanySpec(
        tenant_id="dave-technologies",
        name="Dave Technologies",
        seniority_levels=(
            SeniorityLevelSpec("junior", 1),
            SeniorityLevelSpec("senior", 3),
            SeniorityLevelSpec("lead", 5),
        ),
        roles=(
            RoleSpec(
                id="manager",
                allowed_tools=("mcp-company.*",),
                memory_namespaces=("company",),
                approval_rules=("production_change",),
            ),
            RoleSpec(id="platform", allowed_tools=("mcp-docker.*", "mcp-kubernetes.*")),
        ),
        departments=(
            DepartmentSpec(id="infra", name="Infrastructure", allowed_tools=("mcp-vault.*",)),
            DepartmentSpec(
                id="hosting",
                name="Hosting",
                parent_id="infra",
                allowed_tools=("mcp-proxmox.*",),
                memory_namespaces=("infra/hosting",),
                approval_rules=("red_requires_ceo",),
            ),
        ),
        agents=(
            AgentSpec(
                id="consulting-agent",
                department_id="infra",
                role="manager",
                seniority="lead",
                is_manager=True,
            ),
            AgentSpec(
                id="platform-agent",
                department_id="hosting",
                role="platform",
                seniority="senior",
                reports_to="consulting-agent",
            ),
        ),
    )


def test_company_spec_preview_validates_without_writing():
    report = preview_company(_spec())
    assert report.applied is False
    assert report.department_count == 2
    assert report.agent_count == 2


def test_bootstrap_company_writes_through_org_store():
    store = make_org_store("sqlite://")
    report = bootstrap_company(_spec(), store=store)
    assert report.applied is True

    org = load_org("dave-technologies", store=store)
    members = {member.name: member for member in org.members(recursive=True)}
    assert set(members) == {"consulting-agent", "platform-agent"}
    assert members["platform-agent"].seniority == 3
    assert members["platform-agent"].seat.permissions == {
        "mcp-docker.*",
        "mcp-kubernetes.*",
    }
    hosting = next(node for node in org.walk() if node.name == "Hosting")
    assert hosting.grants == {"mcp-proxmox.*"}
    policy_names = {ref.name for ref in org.policy_refs}
    assert "memory_namespace:hosting:infra/hosting" in policy_names
    assert "approval_rule:hosting:red_requires_ceo" in policy_names


def test_bootstrap_company_is_idempotent_for_members():
    store = make_org_store("sqlite://")
    bootstrap_company(_spec(), store=store)
    bootstrap_company(_spec(), store=store)
    org = load_org("dave-technologies", store=store)
    assert [member.name for member in org.members(recursive=True)].count("platform-agent") == 1


def test_company_spec_rejects_unknown_department_role_and_report_target():
    with pytest.raises(ValueError, match="unknown department"):
        CompanySpec(
            tenant_id="x",
            name="X",
            departments=(),
            roles=(RoleSpec("manager"),),
            agents=(AgentSpec("a", department_id="missing", role="manager"),),
        ).validate()

    with pytest.raises(ValueError, match="unknown role"):
        CompanySpec(
            tenant_id="x",
            name="X",
            departments=(DepartmentSpec("ops", "Ops"),),
            roles=(),
            agents=(AgentSpec("a", department_id="ops", role="missing"),),
        ).validate()

    with pytest.raises(ValueError, match="unknown reports_to"):
        CompanySpec(
            tenant_id="x",
            name="X",
            departments=(DepartmentSpec("ops", "Ops"),),
            roles=(RoleSpec("manager"),),
            agents=(AgentSpec("a", department_id="ops", role="manager", reports_to="ghost"),),
        ).validate()


def test_seniority_rank_uses_spec_then_defaults():
    assert seniority_rank("lead", (SeniorityLevelSpec("lead", 9),)) == 9
    assert seniority_rank("senior") == 3
    assert seniority_rank("unknown") == 0
