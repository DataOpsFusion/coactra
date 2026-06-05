"""Seat — a role grouping that permissions attach to (AD security-group analogue).

A member holds at most one seat (its role). The seat carries the role name, an optional
ownership ``domain`` hint, and the permission set conferred by that role. Seat
permissions are part of the union resolved by ``Organization.can`` — they are the
member's *baseline* authority before node-inherited grants and per-member overrides.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from coactra.directory.domain.permission import Action, PermissionSet


@dataclass(eq=False)
class Seat:
    """A role/seat. ``permissions`` are the actions the role itself confers."""

    role: str
    domain: str | None = None
    permissions: PermissionSet = field(default_factory=set)
    id: int | None = None

    def grants(self, action: Action) -> bool:
        return action in self.permissions
