"""OrgStore — the swappable directory SPI.

Every method takes tenant_id (or a tenant-bearing entity) FIRST; multi-tenant scoping
is part of the contract, not the caller's discipline alone. The default SqliteOrgStore
is the ONE working implementation; the Neo4j adapter is an optional-extra stub. This
contract is a DIRECTORY — it answers ownership and escalation-routing questions. It does
NOT run, mutate, or own work orders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from coactra.organization.models import (
    Department, EscalationRoute, Member, PolicyRef, ReportingEdge, Seat, Tenant,
)


@dataclass
class Directory:
    """A bulk, tenant-scoped read of the whole org — one join the consumer can rebuild
    the tree from without reaching into the store's engine.

    ``nodes`` are the OU rows; ``members`` the principals; ``seat_by_member`` maps a
    member id to its Seat; ``node_by_member`` maps a member id to the node id it sits on.
    """

    tenant_id: str
    nodes: list[Department] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)
    seat_by_member: dict[int, Seat] = field(default_factory=dict)
    node_by_member: dict[int, int | None] = field(default_factory=dict)
    # node id -> set of granted actions; member id -> {action: "allow"|"deny"}
    grants_by_node: dict[int, set[str]] = field(default_factory=dict)
    overrides_by_member: dict[int, dict[str, str]] = field(default_factory=dict)
    seats: list[Seat] = field(default_factory=list)
    reporting_edges: list[ReportingEdge] = field(default_factory=list)
    escalation_routes: list[EscalationRoute] = field(default_factory=list)
    policy_refs: list[PolicyRef] = field(default_factory=list)


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
        seat_id: int | None = None,
        department_id: int | None = None,
    ) -> None:
        """Place a member (department optional => flat fleet). ``seat_id=None`` records a
        seatless placement — a principal on a node without a role."""
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

    # --- READ / directory APIs (the consumer's window — no _engine reaching) ---

    def roots(self, tenant_id: str) -> list[Department]:
        """The tenant's parentless OU nodes (tree roots)."""
        ...

    def children_of(self, tenant_id: str, node_id: int) -> list[Department]:
        """The direct child OU nodes of a node."""
        ...

    def node(self, tenant_id: str, id: int) -> Department | None:
        """Fetch a single OU node by id (tenant-scoped), or None."""
        ...

    def seat_of(self, tenant_id: str, member_id: int) -> Seat | None:
        """The seat a member currently holds, or None if unassigned."""
        ...

    def memberships(
        self, tenant_id: str, node_id: int, recursive: bool = False
    ) -> list[Member]:
        """Members sitting on a node; with recursive=True, the node's whole subtree."""
        ...

    def directory(self, tenant_id: str) -> "Directory":
        """One bulk, tenant-scoped join the consumer can rebuild the tree from."""
        ...

    # --- permission writes/reads (node grants + per-member overrides) ----------

    def grant_node(self, tenant_id: str, node_id: int, action: str) -> None:
        """Grant a node-level permission (idempotent)."""
        ...

    def revoke_node(self, tenant_id: str, node_id: int, action: str) -> None:
        """Remove a node-level grant (no-op if absent)."""
        ...

    def grants_of(self, tenant_id: str, node_id: int) -> set[str]:
        """The actions granted at a node."""
        ...

    def set_override(
        self, tenant_id: str, member_id: int, action: str, effect: str
    ) -> None:
        """Set a per-member explicit allow/deny override (upsert)."""
        ...

    def overrides_of(self, tenant_id: str, member_id: int) -> dict[str, str]:
        """A member's explicit overrides as ``{action: 'allow'|'deny'}``."""
        ...

    # --- mutation reconciliation (so an explicit re-save flushes changes) -------

    def set_member_status(self, tenant_id: str, member_id: int, status: str) -> None:
        """Persist a member's lifecycle status (active/suspended/archived)."""
        ...

    def set_member_directory_fields(
        self, tenant_id: str, member_id: int, *, seniority: int, created_by: str | None, approved_by: str | None
    ) -> None:
        """Persist directory ranking and audit attribution fields."""
        ...

    def set_block_inheritance(self, tenant_id: str, node_id: int, value: bool) -> None:
        """Persist a node's block_inheritance flag."""
        ...

    def place_member(
        self, tenant_id: str, member_id: int, node_id: int | None, seat_id: int | None
    ) -> None:
        """Upsert a member's single placement row (node + optional seat) — no duplicate
        Membership rows on re-save / move."""
        ...

    def clear_override(self, tenant_id: str, member_id: int, action: str) -> None:
        """Remove one per-member override (no-op if absent)."""
        ...


# Single source of truth for the directory SPI surface. Adapters (the async facade and the
# tenant router) build their forwarders from this instead of hand-syncing a name list that
# can silently drift from the Protocol — add a method here and both adapters pick it up.
ORG_STORE_METHODS: tuple[str, ...] = tuple(
    name for name, value in vars(OrgStore).items()
    if not name.startswith("_") and callable(value)
)
