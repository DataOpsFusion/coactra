from fleetlib.organization import (
    Department,
    Member,
    OrgStore,
    PolicyRef,
    Seat,
    Tenant,
)


class _Dummy:
    """A no-op class that implements the FULL OrgStore surface — proves the
    Protocol's method set is exactly the swap contract a backend must satisfy."""

    def add_tenant(self, tenant: Tenant) -> Tenant:
        return tenant

    def add_seat(self, tenant_id: str, seat: Seat) -> Seat:
        return seat

    def add_member(self, tenant_id: str, member: Member) -> Member:
        return member

    def assign(self, tenant_id, member_id, seat_id, department_id=None) -> None:
        ...

    def members(self, tenant_id: str) -> list[Member]:
        return []

    def add_department(self, tenant_id: str, department: Department) -> Department:
        return department

    def reports_to(self, tenant_id, seat_id, reports_to_seat_id) -> None:
        ...

    def manager_of(self, tenant_id: str, seat_id: int):
        return None

    def set_escalation_route(self, tenant_id, from_seat_id, to_seat_id) -> None:
        ...

    def escalate(self, tenant_id: str, seat_id: int):
        return None

    def owner_of(self, tenant_id: str, resource_domain: str):
        return None

    def add_policy_ref(self, tenant_id: str, policy_ref: PolicyRef) -> PolicyRef:
        return policy_ref

    def policy_ref(self, tenant_id: str, name: str, version: int | None = None):
        return None


def test_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), OrgStore)


def test_incomplete_class_is_not_a_store():
    class Partial:
        def members(self, tenant_id):
            return []

    assert not isinstance(Partial(), OrgStore)
