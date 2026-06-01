from coactra.organization import (
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

    # READ / directory APIs added in the v0.2 redesign — the swap contract grew.
    def roots(self, tenant_id: str):
        return []

    def children_of(self, tenant_id: str, node_id: int):
        return []

    def node(self, tenant_id: str, id: int):
        return None

    def seat_of(self, tenant_id: str, member_id: int):
        return None

    def memberships(self, tenant_id: str, node_id: int, recursive: bool = False):
        return []

    def directory(self, tenant_id: str):
        return None

    def grant_node(self, tenant_id: str, node_id: int, action: str) -> None:
        ...

    def revoke_node(self, tenant_id: str, node_id: int, action: str) -> None:
        ...

    def grants_of(self, tenant_id: str, node_id: int):
        return set()

    def set_override(self, tenant_id, member_id, action, effect) -> None:
        ...

    def overrides_of(self, tenant_id: str, member_id: int):
        return {}

    def set_member_status(self, tenant_id, member_id, status) -> None:
        ...

    def set_block_inheritance(self, tenant_id, node_id, value) -> None:
        ...

    def place_member(self, tenant_id, member_id, node_id, seat_id) -> None:
        ...

    def clear_override(self, tenant_id, member_id, action) -> None:
        ...


def test_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), OrgStore)


def test_incomplete_class_is_not_a_store():
    class Partial:
        def members(self, tenant_id):
            return []

    assert not isinstance(Partial(), OrgStore)
