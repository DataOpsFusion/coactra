"""Domain layer — the rich OOP model (behavior lives here).

``Organization`` is the composite OU-tree aggregate; ``Member``/``Seat`` are the
principal and role grouping; ``permission`` carries the action/override primitives.
These are in-memory domain objects, distinct from the ``models`` SQLModel rows that
persist them (the deliberate domain/persistence split of the v0.2 redesign).
"""

from __future__ import annotations

from coactra.directory.domain.directory import PolicyReference
from coactra.directory.domain.member import Member, MemberKind, MemberStatus
from coactra.directory.domain.organization import Organization
from coactra.directory.domain.permission import Action, Effect, PermissionSet
from coactra.directory.domain.seat import Seat

__all__ = [
    "Organization",
    "Member",
    "MemberKind",
    "MemberStatus",
    "Seat",
    "Action",
    "Effect",
    "PermissionSet",
    "PolicyReference",
]
