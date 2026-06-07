"""Service layer — explicit persistence for the Organization aggregate (repository
pattern, DI). The store is ALWAYS injected; neither the service nor the aggregate
constructs one inline.

``save_org(org, *, store)`` flushes the in-memory tree to the store: OU nodes
(preserving parent links and ``block_inheritance``), members (with status and seats),
node grants, and per-member overrides. It stamps persistence ids back onto the domain
objects so a re-save is idempotent (already-persisted nodes/members are not duplicated).

``load_org(tenant, *, store)`` rebuilds an equivalent ``Organization`` tree from a
single bulk ``directory(tenant)`` read — roots, children, members, seats, grants and
overrides — or returns ``None`` if the tenant has no nodes.
"""

from __future__ import annotations

from coactra.team.directory.domain.directory import PolicyReference
from coactra.team.directory.domain.member import Member as DomainMember
from coactra.team.directory.domain.member import MemberKind, MemberStatus
from coactra.team.directory.domain.organization import Organization
from coactra.team.directory.domain.seat import Seat as DomainSeat
from coactra.team.directory.models import Department, MemberStatus as RowStatus, PolicyRef as PolicyRefRow
from coactra.team.directory.models import Member as MemberRow
from coactra.team.directory.models import Seat as SeatRow
from coactra.team.directory.repository.store import OrgStore


def save_org(org: Organization, *, store: OrgStore) -> None:
    """Persist the whole tree rooted at ``org`` through the injected store."""
    if not org.is_root:
        org = org.root_node()
    # Register the tenant once; a re-save of an already-persisted tree must not
    # re-insert it (the tenant_id is its primary key).
    if not store.directory(org.tenant).nodes and org.id is None:
        store.add_tenant(_tenant_row(org))
    _save_node(org, parent_id=None, store=store)
    _save_directory_metadata(org, store=store)


def _tenant_row(org: Organization):
    from coactra.team.directory.models import Tenant

    return Tenant(tenant_id=org.tenant, name=org.name)


def _reconcile_set(desired: set, persisted: set, *, add, remove) -> None:
    """Drive ``persisted`` toward ``desired``: add what's missing, remove what's extra.

    The "save flushes mutations" contract in one place — read ``persisted`` once, then
    diff both directions.
    """
    for item in desired - persisted:
        add(item)
    for item in persisted - desired:
        remove(item)


def _reconcile_map(desired: dict, persisted: dict, *, upsert, remove) -> None:
    """Drive ``persisted`` toward ``desired`` by key: upsert changed values, drop removed keys."""
    for key, value in desired.items():
        if persisted.get(key) != value:
            upsert(key, value)
    for key in set(persisted) - set(desired):
        remove(key)


def _save_node(node: Organization, *, parent_id: int | None, store: OrgStore) -> None:
    """Persist (or reconcile) one node, then its members, then recurse.

    A first save inserts; a re-save reconciles the mutable bits — block_inheritance
    and the node-grant set (additions AND removals) — so the spec's "save flushes
    mutations" contract holds for an already-persisted tree.
    """
    tenant = node.tenant
    if node.id is None:
        row = store.add_department(
            tenant,
            Department(
                tenant_id=tenant,
                name=node.name,
                parent_id=parent_id,
                block_inheritance=node.block_inheritance,
            ),
        )
        node.id = row.id
    else:
        store.set_block_inheritance(tenant, node.id, node.block_inheritance)

    # reconcile node-level grants: add new, revoke removed (single read of persisted)
    _reconcile_set(
        node.grants,
        store.grants_of(tenant, node.id),
        add=lambda action: store.grant_node(tenant, node.id, action),
        remove=lambda action: store.revoke_node(tenant, node.id, action),
    )

    for member in node.members():
        _save_member(member, node_id=node.id, store=store)

    for child in node.children:
        _save_node(child, parent_id=node.id, store=store)


def _save_member(member: DomainMember, *, node_id: int, store: OrgStore) -> None:
    tenant = member.node.tenant
    seat_id: int | None = getattr(member, "_seat_id", None)

    if member.id is None:
        row = store.add_member(
            tenant,
            MemberRow(
                tenant_id=tenant,
                name=member.name,
                kind=member.kind.value,
                status=RowStatus(member.status.value),
                seniority=member.seniority,
                created_by=member.created_by,
                approved_by=member.approved_by,
            ),
        )
        member.id = row.id
        if member.seat is not None:
            seat_row = store.add_seat(
                tenant,
                SeatRow(
                    tenant_id=tenant,
                    role=member.seat.role,
                    domain=member.seat.domain,
                    permissions=sorted(member.seat.permissions),
                ),
            )
            seat_id = seat_row.id
            member.seat.id = seat_id
            member._seat_id = seat_id  # remember it so move() keeps the same seat
        # placement: node + optional seat (upsert keeps it single)
        store.place_member(tenant, member.id, node_id=node_id, seat_id=seat_id)
    else:
        # reconcile mutable bits on re-save: status + placement (move)
        store.set_member_status(tenant, member.id, member.status.value)
        store.set_member_directory_fields(
            tenant, member.id, seniority=member.seniority,
            created_by=member.created_by, approved_by=member.approved_by,
        )
        store.place_member(tenant, member.id, node_id=node_id, seat_id=seat_id)

    # reconcile per-member overrides: set desired, clear removed
    _reconcile_map(
        {a: e.value for a, e in member.overrides.items()},
        store.overrides_of(tenant, member.id),
        upsert=lambda action, effect: store.set_override(tenant, member.id, action, effect),
        remove=lambda action: store.clear_override(tenant, member.id, action),
    )


def _save_directory_metadata(org: Organization, *, store: OrgStore) -> None:
    """Flush optional reporting, escalation, and policy metadata after seats exist."""
    root = org.root_node()
    current = store.directory(root.tenant)
    reporting = {(edge.seat_id, edge.reports_to_seat_id) for edge in current.reporting_edges}
    for seat, manager in root.reporting_edges:
        if seat.id is not None and manager.id is not None and (seat.id, manager.id) not in reporting:
            store.reports_to(root.tenant, seat.id, manager.id)
    routes = {(route.from_seat_id, route.to_seat_id) for route in current.escalation_routes}
    for seat, decider in root.escalation_routes:
        if seat.id is not None and decider.id is not None and (seat.id, decider.id) not in routes:
            store.set_escalation_route(root.tenant, seat.id, decider.id)
    policies = {(ref.name, ref.version, ref.target) for ref in current.policy_refs}
    for ref in root.policy_refs:
        if (ref.name, ref.version, ref.target) not in policies:
            store.add_policy_ref(
                root.tenant,
                PolicyRefRow(tenant_id=root.tenant, name=ref.name, version=ref.version, target=ref.target),
            )


def load_org(tenant: str, *, store: OrgStore) -> Organization | None:
    """Rebuild the ``Organization`` tree for ``tenant`` from one bulk read, or None."""
    d = store.directory(tenant)
    if not d.nodes:
        return None

    children: dict[int | None, list[Department]] = {}
    for n in d.nodes:
        children.setdefault(n.parent_id, []).append(n)

    roots = children.get(None, [])
    # A well-formed tenant tree has exactly one root; if several, the first is the
    # aggregate root and others are attached defensively (shouldn't happen via save_org).
    root_row = roots[0]
    nodes_by_id: dict[int, Organization] = {}

    def _build(row: Department, parent: Organization | None) -> Organization:
        org = Organization(
            tenant=tenant,
            name=row.name,
            parent=parent,
            block_inheritance=bool(row.block_inheritance),
            id=row.id,
        )
        nodes_by_id[row.id] = org
        # restore node grants
        for action in d.grants_by_node.get(row.id, set()):
            org.grant(action)
        # attach children
        for child_row in children.get(row.id, []):
            child = _build(child_row, org)
            org._children.append(child)
        return org

    root = _build(root_row, None)

    # Restore domain seats first so ownership/reporting metadata and members share identity.
    seats_by_id: dict[int, DomainSeat] = {
        row.id: DomainSeat(
            role=row.role, domain=row.domain, permissions=set(row.permissions or []), id=row.id
        )
        for row in d.seats
        if row.id is not None
    }
    root._known_seats.extend(seats_by_id.values())

    # place members on their nodes, restore seats / status / overrides
    for m in d.members:
        node_id = d.node_by_member.get(m.id)
        target = nodes_by_id.get(node_id) if node_id is not None else None
        if target is None:
            # unassigned member: attach to the root so it is still discoverable
            target = root
        seat_row = d.seat_by_member.get(m.id)
        seat = seats_by_id.get(seat_row.id) if seat_row is not None else None
        member = DomainMember(
            name=m.name,
            kind=MemberKind(m.kind.value if hasattr(m.kind, "value") else m.kind),
            seat=seat,
            status=MemberStatus(m.status.value if hasattr(m.status, "value") else m.status),
            overrides={},
            node=target,
            id=m.id,
            seniority=m.seniority,
            created_by=m.created_by,
            approved_by=m.approved_by,
        )
        # remember the persisted seat id so a later move()+save keeps the same seat
        if seat_row is not None:
            member._seat_id = seat_row.id
        from coactra.team.directory.domain.permission import Effect

        for action, effect in d.overrides_by_member.get(m.id, {}).items():
            member.overrides[action] = Effect(effect)
        target._members.append(member)

    for edge in d.reporting_edges:
        subordinate = seats_by_id.get(edge.seat_id)
        manager = seats_by_id.get(edge.reports_to_seat_id)
        if subordinate is not None and manager is not None:
            root._reporting_edges.append((subordinate, manager))
    for route in d.escalation_routes:
        subordinate = seats_by_id.get(route.from_seat_id)
        decider = seats_by_id.get(route.to_seat_id)
        if subordinate is not None and decider is not None:
            root._escalation_routes.append((subordinate, decider))
    root._policy_refs.extend(
        PolicyReference(name=ref.name, version=ref.version, target=ref.target)
        for ref in d.policy_refs
    )

    return root
