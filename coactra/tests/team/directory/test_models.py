from coactra.team.directory import (
    Department,
    EscalationRoute,
    Member,
    MemberKind,
    Membership,
    PolicyRef,
    ReportingEdge,
    Seat,
    Tenant,
)


def test_member_kind_values():
    assert {k.value for k in MemberKind} == {"human", "service", "agent"}


def test_flat_member_needs_no_department():
    # Baseline fleet shape: a member exists in a tenant with just a kind/name.
    m = Member(tenant_id="acme", name="alice", kind=MemberKind.human)
    assert m.tenant_id == "acme"
    assert m.kind is MemberKind.human


def test_membership_department_is_optional():
    ms = Membership(tenant_id="acme", member_id=1, seat_id=2)
    assert ms.department_id is None  # hierarchy is additive, never required


def test_entities_carry_tenant_id():
    for cls in (Tenant, Department, Seat, Member, Membership, ReportingEdge, EscalationRoute, PolicyRef):
        assert "tenant_id" in cls.model_fields


def test_seat_has_role_and_optional_domain():
    s = Seat(tenant_id="acme", role="platform", domain="infrastructure")
    assert s.role == "platform"
    assert s.domain == "infrastructure"
