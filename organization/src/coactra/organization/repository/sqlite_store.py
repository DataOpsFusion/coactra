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

from coactra.organization.engine import make_engine
from coactra.organization.errors import CrossTenantError
from coactra.organization.models import (
    Department,
    EscalationRoute,
    Member,
    MemberOverride,
    Membership,
    NodeGrant,
    PolicyRef,
    ReportingEdge,
    Seat,
    Tenant,
)
from coactra.organization.repository.store import Directory


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
        seat_id: int | None = None,
        department_id: int | None = None,
    ) -> None:
        # member (and seat, when given) must belong to this tenant. seat_id=None records
        # a seatless placement — the principal sits on a node without holding a role.
        with Session(self._engine) as s:
            member = s.get(Member, member_id)
            if member is None or member.tenant_id != tenant_id:
                raise CrossTenantError(
                    f"member_id={member_id} not in tenant {tenant_id!r}"
                )
            if seat_id is not None:
                seat = s.get(Seat, seat_id)
                if seat is None or seat.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"seat_id={seat_id} not in tenant {tenant_id!r}"
                    )
            if department_id is not None:
                department = s.get(Department, department_id)
                if department is None or department.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"department_id={department_id} not in tenant {tenant_id!r}"
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

    # --- READ / directory APIs (the consumer's window — no _engine reaching) ---

    def roots(self, tenant_id: str) -> list[Department]:
        with Session(self._engine) as s:
            return list(
                s.exec(
                    select(Department).where(
                        Department.tenant_id == tenant_id,
                        Department.parent_id.is_(None),
                    )
                ).all()
            )

    def children_of(self, tenant_id: str, node_id: int) -> list[Department]:
        with Session(self._engine) as s:
            return list(
                s.exec(
                    select(Department).where(
                        Department.tenant_id == tenant_id,
                        Department.parent_id == node_id,
                    )
                ).all()
            )

    def node(self, tenant_id: str, id: int) -> Department | None:
        with Session(self._engine) as s:
            dept = s.get(Department, id)
            if dept is None or dept.tenant_id != tenant_id:
                return None
            return dept

    def seat_of(self, tenant_id: str, member_id: int) -> Seat | None:
        with Session(self._engine) as s:
            ms = s.exec(
                select(Membership).where(
                    Membership.tenant_id == tenant_id,
                    Membership.member_id == member_id,
                )
            ).first()
            if ms is None or ms.seat_id is None:
                return None
            return s.get(Seat, ms.seat_id)

    def _descendant_ids(self, s: Session, tenant_id: str, node_id: int) -> set[int]:
        """node_id plus every descendant id (in-tenant), via a BFS over parent_id."""
        ids: set[int] = {node_id}
        frontier = [node_id]
        while frontier:
            kids = s.exec(
                select(Department.id).where(
                    Department.tenant_id == tenant_id,
                    Department.parent_id.in_(frontier),
                )
            ).all()
            new = [k for k in kids if k not in ids]
            ids.update(new)
            frontier = new
        return ids

    def memberships(
        self, tenant_id: str, node_id: int, recursive: bool = False
    ) -> list[Member]:
        with Session(self._engine) as s:
            scope = (
                self._descendant_ids(s, tenant_id, node_id)
                if recursive
                else {node_id}
            )
            rows = s.exec(
                select(Member)
                .join(Membership, Membership.member_id == Member.id)
                .where(
                    Membership.tenant_id == tenant_id,
                    Membership.department_id.in_(scope),
                )
            ).all()
            return list(rows)

    def directory(self, tenant_id: str) -> Directory:
        with Session(self._engine) as s:
            nodes = list(
                s.exec(
                    select(Department).where(Department.tenant_id == tenant_id)
                ).all()
            )
            members = list(
                s.exec(select(Member).where(Member.tenant_id == tenant_id)).all()
            )
            seat_by_member: dict[int, Seat] = {}
            node_by_member: dict[int, int | None] = {}
            for ms in s.exec(
                select(Membership).where(Membership.tenant_id == tenant_id)
            ).all():
                node_by_member[ms.member_id] = ms.department_id
                if ms.seat_id is not None:
                    seat = s.get(Seat, ms.seat_id)
                    if seat is not None:
                        seat_by_member[ms.member_id] = seat
            grants_by_node: dict[int, set[str]] = {}
            for g in s.exec(
                select(NodeGrant).where(NodeGrant.tenant_id == tenant_id)
            ).all():
                grants_by_node.setdefault(g.node_id, set()).add(g.action)
            overrides_by_member: dict[int, dict[str, str]] = {}
            for o in s.exec(
                select(MemberOverride).where(MemberOverride.tenant_id == tenant_id)
            ).all():
                overrides_by_member.setdefault(o.member_id, {})[o.action] = o.effect
            return Directory(
                tenant_id=tenant_id,
                nodes=nodes,
                members=members,
                seat_by_member=seat_by_member,
                node_by_member=node_by_member,
                grants_by_node=grants_by_node,
                overrides_by_member=overrides_by_member,
            )

    # --- permission writes/reads (node grants + per-member overrides) ----------

    def grant_node(self, tenant_id: str, node_id: int, action: str) -> None:
        with Session(self._engine) as s:
            node = s.get(Department, node_id)
            if node is None or node.tenant_id != tenant_id:
                raise CrossTenantError(
                    f"node_id={node_id} not in tenant {tenant_id!r}; grant refused"
                )
            existing = s.exec(
                select(NodeGrant).where(
                    NodeGrant.tenant_id == tenant_id,
                    NodeGrant.node_id == node_id,
                    NodeGrant.action == action,
                )
            ).first()
            if existing is None:
                s.add(NodeGrant(tenant_id=tenant_id, node_id=node_id, action=action))
                s.commit()

    def revoke_node(self, tenant_id: str, node_id: int, action: str) -> None:
        with Session(self._engine) as s:
            existing = s.exec(
                select(NodeGrant).where(
                    NodeGrant.tenant_id == tenant_id,
                    NodeGrant.node_id == node_id,
                    NodeGrant.action == action,
                )
            ).first()
            if existing is not None:
                s.delete(existing)
                s.commit()

    def grants_of(self, tenant_id: str, node_id: int) -> set[str]:
        with Session(self._engine) as s:
            rows = s.exec(
                select(NodeGrant.action).where(
                    NodeGrant.tenant_id == tenant_id,
                    NodeGrant.node_id == node_id,
                )
            ).all()
            return set(rows)

    def set_override(
        self, tenant_id: str, member_id: int, action: str, effect: str
    ) -> None:
        with Session(self._engine) as s:
            member = s.get(Member, member_id)
            if member is None or member.tenant_id != tenant_id:
                raise CrossTenantError(
                    f"member_id={member_id} not in tenant {tenant_id!r}; override refused"
                )
            existing = s.exec(
                select(MemberOverride).where(
                    MemberOverride.tenant_id == tenant_id,
                    MemberOverride.member_id == member_id,
                    MemberOverride.action == action,
                )
            ).first()
            if existing is not None:
                existing.effect = effect
                s.add(existing)
            else:
                s.add(
                    MemberOverride(
                        tenant_id=tenant_id,
                        member_id=member_id,
                        action=action,
                        effect=effect,
                    )
                )
            s.commit()

    def overrides_of(self, tenant_id: str, member_id: int) -> dict[str, str]:
        with Session(self._engine) as s:
            rows = s.exec(
                select(MemberOverride).where(
                    MemberOverride.tenant_id == tenant_id,
                    MemberOverride.member_id == member_id,
                )
            ).all()
            return {o.action: o.effect for o in rows}

    # --- mutation reconciliation (so an explicit re-save flushes changes) -------

    def set_member_status(self, tenant_id: str, member_id: int, status: str) -> None:
        with Session(self._engine) as s:
            member = s.get(Member, member_id)
            if member is None or member.tenant_id != tenant_id:
                raise CrossTenantError(
                    f"member_id={member_id} not in tenant {tenant_id!r}"
                )
            member.status = status
            s.add(member)
            s.commit()

    def set_block_inheritance(self, tenant_id: str, node_id: int, value: bool) -> None:
        with Session(self._engine) as s:
            node = s.get(Department, node_id)
            if node is None or node.tenant_id != tenant_id:
                raise CrossTenantError(
                    f"node_id={node_id} not in tenant {tenant_id!r}"
                )
            node.block_inheritance = value
            s.add(node)
            s.commit()

    def place_member(
        self, tenant_id: str, member_id: int, node_id: int | None, seat_id: int | None
    ) -> None:
        with Session(self._engine) as s:
            member = s.get(Member, member_id)
            if member is None or member.tenant_id != tenant_id:
                raise CrossTenantError(
                    f"member_id={member_id} not in tenant {tenant_id!r}"
                )
            if seat_id is not None:
                seat = s.get(Seat, seat_id)
                if seat is None or seat.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"seat_id={seat_id} not in tenant {tenant_id!r}"
                    )
            if node_id is not None:
                node = s.get(Department, node_id)
                if node is None or node.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"node_id={node_id} not in tenant {tenant_id!r}"
                    )
            existing = s.exec(
                select(Membership).where(
                    Membership.tenant_id == tenant_id,
                    Membership.member_id == member_id,
                )
            ).first()
            if existing is None:
                s.add(
                    Membership(
                        tenant_id=tenant_id,
                        member_id=member_id,
                        seat_id=seat_id,
                        department_id=node_id,
                    )
                )
            else:
                existing.department_id = node_id
                existing.seat_id = seat_id
                s.add(existing)
            s.commit()

    def clear_override(self, tenant_id: str, member_id: int, action: str) -> None:
        with Session(self._engine) as s:
            existing = s.exec(
                select(MemberOverride).where(
                    MemberOverride.tenant_id == tenant_id,
                    MemberOverride.member_id == member_id,
                    MemberOverride.action == action,
                )
            ).first()
            if existing is not None:
                s.delete(existing)
                s.commit()
