"""Member — a principal (human / service / agent) living on exactly one OU node.

A member holds an optional ``Seat`` (its role), a lifecycle ``status`` (active vs
suspended), and an optional set of per-member permission ``overrides`` (explicit
allow/deny on individual actions). It knows its node, so it can compute its DN.

A member is a *domain* object, distinct from the ``models.Member`` SQLModel row that
persists it — this is the deliberate domain/persistence split of the v0.2 redesign.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from coactra.organization.domain.permission import Action, Effect
from coactra.organization.domain.seat import Seat

if TYPE_CHECKING:
    from coactra.organization.domain.organization import Organization


class MemberKind(str, Enum):
    """What sort of principal this is. Mirrors models.MemberKind values."""

    human = "human"
    service = "service"
    agent = "agent"


class MemberStatus(str, Enum):
    """Lifecycle state. Suspended is reversible (disable); removal deletes outright."""

    active = "active"
    suspended = "suspended"


@dataclass(eq=False)
class Member:
    """A principal occupying one seat on one node.

    ``overrides`` map an action to an explicit allow/deny that wins over everything
    else in resolution (deny beats allow). ``id`` is the persistence identity, set once
    the member has been saved/loaded; it is ``None`` for a freshly hired in-memory
    principal.
    """

    name: str
    kind: MemberKind = MemberKind.agent
    seat: Seat | None = None
    status: MemberStatus = MemberStatus.active
    overrides: dict[Action, Effect] = field(default_factory=dict)
    node: "Organization | None" = None
    id: int | None = None

    @property
    def active(self) -> bool:
        return self.status is MemberStatus.active

    @property
    def dn(self) -> str:
        """DN-style path: the node's path with this member's name appended."""
        if self.node is None:
            return self.name
        return f"{self.node.path}/{self.name}"

    def allow(self, action: Action) -> None:
        """Set an explicit allow override for one action."""
        self.overrides[action] = Effect.allow

    def deny(self, action: Action) -> None:
        """Set an explicit deny override for one action (wins over any grant)."""
        self.overrides[action] = Effect.deny

    def role_permissions(self) -> set[Action]:
        return set(self.seat.permissions) if self.seat is not None else set()
