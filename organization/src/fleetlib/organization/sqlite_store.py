"""SqliteOrgStore — the ONE working default OrgStore.

SQLite via sqlmodel. Tenant-isolated by FILTER DISCIPLINE: every read carries a
WHERE tenant_id = ? and every cross-tenant write raises CrossTenantError. In SQL,
isolation is not structural (unlike a dict keyed by tenant) — so the guards here ARE
the invariant. escalate() is a routing query; this store covers the CRUD core,
optional hierarchy, escalation routing, ownership, and versioned policy refs.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from fleetlib.organization.engine import make_engine
from fleetlib.organization.errors import CrossTenantError
from fleetlib.organization.models import (
    Department,
    EscalationRoute,
    Member,
    Membership,
    PolicyRef,
    ReportingEdge,
    Seat,
    Tenant,
)


class SqliteOrgStore:
    """In-memory (default) or file-backed SQLite directory store."""

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or make_engine()

    def _check(self, tenant_id: str, entity) -> None:
        # A tenant-bearing entity must match the operation's tenant_id, or it's a breach.
        if getattr(entity, "tenant_id", tenant_id) != tenant_id:
            raise CrossTenantError(
                f"entity tenant_id={entity.tenant_id!r} != operation tenant_id={tenant_id!r}"
            )

    # --- tenants / seats / members / assignment (flat-fleet baseline) ----------

    def add_tenant(self, tenant: Tenant) -> Tenant:
        with Session(self._engine) as s:
            s.add(tenant)
            s.commit()
            s.refresh(tenant)
            return tenant

    def add_seat(self, tenant_id: str, seat: Seat) -> Seat:
        self._check(tenant_id, seat)
        with Session(self._engine) as s:
            s.add(seat)
            s.commit()
            s.refresh(seat)
            return seat

    def add_member(self, tenant_id: str, member: Member) -> Member:
        self._check(tenant_id, member)
        with Session(self._engine) as s:
            s.add(member)
            s.commit()
            s.refresh(member)
            return member

    def assign(
        self,
        tenant_id: str,
        member_id: int,
        seat_id: int,
        department_id: int | None = None,
    ) -> None:
        # member and seat must both belong to this tenant.
        with Session(self._engine) as s:
            member = s.get(Member, member_id)
            seat = s.get(Seat, seat_id)
            for ent in (member, seat):
                if ent is None or ent.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"member_id={member_id}/seat_id={seat_id} not both in tenant {tenant_id!r}"
                    )
            s.add(
                Membership(
                    tenant_id=tenant_id,
                    member_id=member_id,
                    seat_id=seat_id,
                    department_id=department_id,
                )
            )
            s.commit()

    def members(self, tenant_id: str) -> list[Member]:
        with Session(self._engine) as s:
            return list(s.exec(select(Member).where(Member.tenant_id == tenant_id)).all())

    # --- hierarchy (optional, first-class) -------------------------------------

    def add_department(self, tenant_id: str, department: Department) -> Department:
        self._check(tenant_id, department)
        with Session(self._engine) as s:
            s.add(department)
            s.commit()
            s.refresh(department)
            return department

    def reports_to(self, tenant_id: str, seat_id: int, reports_to_seat_id: int) -> None:
        with Session(self._engine) as s:
            for sid in (seat_id, reports_to_seat_id):
                seat = s.get(Seat, sid)
                if seat is None or seat.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"seat_id={sid} not in tenant {tenant_id!r}; reporting edge refused"
                    )
            s.add(
                ReportingEdge(
                    tenant_id=tenant_id,
                    seat_id=seat_id,
                    reports_to_seat_id=reports_to_seat_id,
                )
            )
            s.commit()

    def manager_of(self, tenant_id: str, seat_id: int) -> Seat | None:
        with Session(self._engine) as s:
            edge = s.exec(
                select(ReportingEdge).where(
                    ReportingEdge.tenant_id == tenant_id,
                    ReportingEdge.seat_id == seat_id,
                )
            ).first()
            if edge is None:
                return None
            return s.get(Seat, edge.reports_to_seat_id)

    # --- escalation ROUTING (query only — no execution, no work-order ownership) ---

    def set_escalation_route(self, tenant_id: str, from_seat_id: int, to_seat_id: int) -> None:
        with Session(self._engine) as s:
            for sid in (from_seat_id, to_seat_id):
                seat = s.get(Seat, sid)
                if seat is None or seat.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"seat_id={sid} not in tenant {tenant_id!r}; route refused"
                    )
            s.add(
                EscalationRoute(
                    tenant_id=tenant_id, from_seat_id=from_seat_id, to_seat_id=to_seat_id
                )
            )
            s.commit()

    def escalate(self, tenant_id: str, seat_id: int) -> Seat | None:
        """Return the seat one tier up. Explicit EscalationRoute wins over the reporting
        edge. This is a LOOKUP — it does not run, mutate, or own a work order."""
        with Session(self._engine) as s:
            route = s.exec(
                select(EscalationRoute).where(
                    EscalationRoute.tenant_id == tenant_id,
                    EscalationRoute.from_seat_id == seat_id,
                )
            ).first()
            if route is not None:
                return s.get(Seat, route.to_seat_id)
        return self.manager_of(tenant_id, seat_id)

    def resolve_decider(self, tenant_id: str, seat_id: int) -> Seat | None:
        """Walk escalate() to the top of the chain and return the final decider seat.
        Still pure routing — the caller decides what to DO with the decider."""
        current_id = seat_id
        seen: set[int] = set()
        decider: Seat | None = None
        while current_id is not None and current_id not in seen:
            seen.add(current_id)
            nxt = self.escalate(tenant_id, current_id)
            if nxt is None:
                break
            decider = nxt
            current_id = nxt.id
        return decider

    # --- ownership ("who owns this?") ------------------------------------------

    def owner_of(self, tenant_id: str, resource_domain: str) -> Seat | None:
        """The seat in this tenant whose domain owns the resource. Simplest concrete
        ownership model — a domain match, not an ACL."""
        with Session(self._engine) as s:
            return s.exec(
                select(Seat).where(
                    Seat.tenant_id == tenant_id,
                    Seat.domain == resource_domain,
                )
            ).first()

    # --- versioned policy REFERENCES (not a policy engine) ---------------------

    def add_policy_ref(self, tenant_id: str, policy_ref: PolicyRef) -> PolicyRef:
        self._check(tenant_id, policy_ref)
        with Session(self._engine) as s:
            s.add(policy_ref)
            s.commit()
            s.refresh(policy_ref)
            return policy_ref

    def policy_ref(
        self, tenant_id: str, name: str, version: int | None = None
    ) -> PolicyRef | None:
        """version=None => the current (highest) version; otherwise that exact version."""
        with Session(self._engine) as s:
            stmt = select(PolicyRef).where(
                PolicyRef.tenant_id == tenant_id, PolicyRef.name == name
            )
            if version is not None:
                stmt = stmt.where(PolicyRef.version == version)
            else:
                stmt = stmt.order_by(PolicyRef.version.desc())
            return s.exec(stmt).first()
