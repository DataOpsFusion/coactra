"""OrgStore — the swappable directory SPI.

Every method takes tenant_id (or a tenant-bearing entity) FIRST; multi-tenant scoping
is part of the contract, not the caller's discipline alone. The default SqliteOrgStore
is the ONE working implementation; the Neo4j adapter is an optional-extra stub. This
contract is a DIRECTORY — it answers ownership and escalation-routing questions. It does
NOT run, mutate, or own work orders.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fleetlib.organization.models import Department, Member, PolicyRef, Seat, Tenant


@runtime_checkable
class OrgStore(Protocol):
    # --- tenants / seats / members / assignment (flat-fleet baseline) ----------

    def add_tenant(self, tenant: Tenant) -> Tenant:
        """Register a tenant (isolation root)."""
        ...

    def add_seat(self, tenant_id: str, seat: Seat) -> Seat:
        """Create a role/seat within a tenant."""
        ...

    def add_member(self, tenant_id: str, member: Member) -> Member:
        """Add a human/service/agent member within a tenant."""
        ...

    def assign(
        self,
        tenant_id: str,
        member_id: int,
        seat_id: int,
        department_id: int | None = None,
    ) -> None:
        """Assign a member to a seat (department optional => flat fleet)."""
        ...

    def members(self, tenant_id: str) -> list[Member]:
        """List a tenant's members (never another tenant's)."""
        ...

    # --- hierarchy: departments + reporting edges (optional, first-class) ------

    def add_department(self, tenant_id: str, department: Department) -> Department:
        """Create a department (optional grouping inside a tenant)."""
        ...

    def reports_to(self, tenant_id: str, seat_id: int, reports_to_seat_id: int) -> None:
        """Record a reporting edge — the chain of command (optional hierarchy)."""
        ...

    def manager_of(self, tenant_id: str, seat_id: int) -> Seat | None:
        """The seat one reporting tier up (None at the top / flat fleet)."""
        ...

    # --- escalation ROUTING (query only — no execution) -----------------------

    def set_escalation_route(
        self, tenant_id: str, from_seat_id: int, to_seat_id: int
    ) -> None:
        """Record an explicit override route that bypasses the reporting chain."""
        ...

    def escalate(self, tenant_id: str, seat_id: int) -> Seat | None:
        """ROUTING QUERY: return the seat one tier up. Never executes anything."""
        ...

    # --- ownership + versioned policy references ------------------------------

    def owner_of(self, tenant_id: str, resource_domain: str) -> Seat | None:
        """Answer 'who owns this?' — the seat whose domain matches the resource."""
        ...

    def add_policy_ref(self, tenant_id: str, policy_ref: PolicyRef) -> PolicyRef:
        """Record a versioned reference to a policy (not a policy engine)."""
        ...

    def policy_ref(
        self, tenant_id: str, name: str, version: int | None = None
    ) -> PolicyRef | None:
        """Current (highest) version, or a specific version if given."""
        ...
