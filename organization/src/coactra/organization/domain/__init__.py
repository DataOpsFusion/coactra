"""Domain layer — the rich OOP model (behavior lives here).

``Organization`` is the composite OU-tree aggregate; ``Member``/``Seat`` are the
principal and role grouping; ``permission`` carries the action/override primitives.
These are in-memory domain objects, distinct from the ``models`` SQLModel rows that
persist them (the deliberate domain/persistence split of the v0.2 redesign).
"""

from __future__ import annotations

from coactra.organization.domain.directory import PolicyReference
from coactra.organization.domain.member import Member, MemberKind, MemberStatus
from coactra.organization.domain.organization import Organization
from coactra.organization.domain.permission import Action, Effect, PermissionSet
from coactra.organization.domain.seat import Seat

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
