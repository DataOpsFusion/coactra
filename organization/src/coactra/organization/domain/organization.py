"""Organization — the composite OU-tree aggregate with rich behavior.

An ``Organization`` is one node in a multi-tenant OU tree (AD organizational-unit
analogue): it has a parent and children (the composite pattern), holds its own
members (principals) and node-level permission grants, and carries a per-node
``block_inheritance`` flag (AD "Block Inheritance").

The aggregate owns **structure, authority, lifecycle, and permissions** — and nothing
else. ``hire`` records a principal; it does not message, provision, or run anything.

Permission resolution (``can``) walks from the member's node up toward the root,
stopping at any node with ``block_inheritance=True``. A per-member override wins
outright (deny beats allow); otherwise the action is granted iff it is in the union of
the member's role/seat permissions and the node grants encountered on the walked path.
Resolution never crosses the tenant boundary.
"""

from __future__ import annotations

from typing import Iterable

from coactra.organization.domain.member import Member, MemberKind, MemberStatus
from coactra.organization.domain.permission import Action, Effect, PermissionSet
from coactra.organization.domain.seat import Seat
from coactra.organization.errors import CrossTenantError


class Organization:
    """A node in the OU tree. Construct a root with :meth:`root`, never directly."""

    def __init__(
        self,
        *,
        tenant: str,
        name: str,
        parent: "Organization | None" = None,
        block_inheritance: bool = False,
        id: int | None = None,
    ) -> None:
        self.tenant = tenant
        self.name = name
        self.parent = parent
        self.block_inheritance = block_inheritance
        self.id = id
        self._children: list[Organization] = []
        self._members: list[Member] = []
        self._grants: PermissionSet = set()

    # --- construction / tree shape (composite) ---------------------------------

    @classmethod
    def root(cls, tenant: str, name: str) -> "Organization":
        """Create a tenant-root OU node (no parent)."""
        return cls(tenant=tenant, name=name, parent=None)

    def add_child(self, name: str) -> "Organization":
        """Create and attach a child OU under this node (inherits the tenant)."""
        child = Organization(tenant=self.tenant, name=name, parent=self)
        self._children.append(child)
        return child

    @property
    def children(self) -> list["Organization"]:
        return list(self._children)

    @property
    def is_root(self) -> bool:
        return self.parent is None

    @property
    def manager(self) -> "Organization | None":
        """Escalation target: the parent node (the authority one tier up). None at root."""
        return self.parent

    @property
    def path(self) -> str:
        """DN-style path: the tenant id, then each OU node name down to this node.

        The root's display *name* is not part of the path — the leading segment is the
        tenant id (the isolation boundary), matching the spec example ``acme/...``.
        """
        names: list[str] = []
        node: Organization | None = self
        while node is not None and node.parent is not None:
            names.append(node.name)
            node = node.parent
        names.reverse()
        return "/".join([self.tenant, *names])

    @property
    def dn(self) -> str:
        return self.path

    def root_node(self) -> "Organization":
        node: Organization = self
        while node.parent is not None:
            node = node.parent
        return node

    def _path_to_root(self) -> list["Organization"]:
        """This node and its ancestors, nearest-first (self … root)."""
        chain: list[Organization] = []
        node: Organization | None = self
        while node is not None:
            chain.append(node)
            node = node.parent
        return chain

    def walk(self) -> Iterable["Organization"]:
        """Yield this node and every descendant (pre-order)."""
        yield self
        for child in self._children:
            yield from child.walk()

    # --- members / lifecycle ---------------------------------------------------

    def hire(
        self,
        name: str,
        kind: str | MemberKind = MemberKind.agent,
        role: str | None = None,
        permissions: PermissionSet | None = None,
    ) -> Member:
        """Record a principal on THIS node. Does not provision or message anything.

        ``role`` (if given) creates the member's seat; ``permissions`` is the role's
        permission set (the seat's baseline authority).
        """
        perms = set(permissions or set())
        # A seat is created if a role is named OR permissions are conferred — never
        # silently drop permissions just because no role string was given.
        seat = Seat(role=role or "", permissions=perms) if (role is not None or perms) else None
        member = Member(name=name, kind=MemberKind(kind), seat=seat, node=self)
        self._members.append(member)
        return member

    def remove(self, member: Member) -> None:
        """Delete a principal outright (AD delete). Searches the subtree."""
        owner = self._owner_node(member)
        owner._members.remove(member)
        member.node = None

    def suspend(self, member: Member) -> None:
        """Disable a principal (reversible). A suspended member can do nothing."""
        self._owner_node(member)  # validates membership / tenant
        member.status = MemberStatus.suspended

    def unsuspend(self, member: Member) -> None:
        """Re-enable a suspended principal."""
        self._owner_node(member)
        member.status = MemberStatus.active

    def move(self, member: Member, to: "Organization") -> None:
        """Reparent a principal to another node in the SAME tenant (AD move OU)."""
        if to.tenant != self.tenant:
            raise CrossTenantError(
                f"cannot move member into tenant {to.tenant!r} from {self.tenant!r}"
            )
        owner = self._owner_node(member)
        owner._members.remove(member)
        to._members.append(member)
        member.node = to

    def members(self, recursive: bool = False) -> list[Member]:
        """This node's members; with ``recursive=True``, this node plus all descendants."""
        if not recursive:
            return list(self._members)
        out: list[Member] = []
        for node in self.walk():
            out.extend(node._members)
        return out

    def _owner_node(self, member: Member) -> "Organization":
        """The node that actually holds ``member`` (searched from the tree root)."""
        for node in self.root_node().walk():
            if member in node._members:
                if node.tenant != self.tenant:  # defensive; same tree => same tenant
                    raise CrossTenantError("member belongs to a different tenant")
                return node
        raise ValueError(f"member {member.name!r} is not in this organization tree")

    # --- node-level grants -----------------------------------------------------

    def grant(self, action: Action) -> None:
        """Grant a node-level permission (inherits down to descendants)."""
        self._grants.add(action)

    def revoke(self, action: Action) -> None:
        """Remove a node-level grant (no-op if not granted)."""
        self._grants.discard(action)

    @property
    def grants(self) -> PermissionSet:
        return set(self._grants)

    # --- permission resolution (AD-style inheritance) --------------------------

    def can(self, member: Member, action: Action) -> bool:
        """True iff ``member`` is permitted ``action`` under inheritance resolution.

        Resolution is independent of which node it is called on: it keys off the
        member's actual node. Cross-tenant resolution raises.
        """
        if member.node is None:
            raise ValueError(f"member {member.name!r} is not placed on any node")
        if member.node.tenant != self.tenant:
            raise CrossTenantError(
                f"cannot resolve permission across tenants: "
                f"member in {member.node.tenant!r}, asked via {self.tenant!r}"
            )

        # A suspended principal has no effective access, regardless of grants.
        if not member.active:
            return False

        # 1. An explicit per-member override wins outright (deny beats allow).
        override = member.overrides.get(action)
        if override is Effect.deny:
            return False
        if override is Effect.allow:
            return True

        # 2. Union of role/seat perms and node grants on the inheritance path,
        #    walking member-node -> root, stopping AT a block_inheritance node.
        if action in member.role_permissions():
            return True
        for node in member.node._path_to_root():
            if action in node._grants:
                return True
            if node.block_inheritance:
                break  # this node's own grants count; nothing above it does
        return False
