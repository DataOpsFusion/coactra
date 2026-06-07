"""Permissions — the unit of authority that flows down the OU tree.

An ``Action`` is just a string token (``"deploy"``, ``"approve"``). A ``PermissionSet``
is a set of granted actions. A per-member ``Override`` is an explicit allow/deny on a
single action that wins outright over inherited/role permissions (deny beats allow) —
the AD "Enforced"/explicit-ACE analogue.
"""

from __future__ import annotations

from enum import Enum

Action = str
PermissionSet = set[Action]


class Effect(str, Enum):
    """An explicit per-member decision on one action."""

    allow = "allow"
    deny = "deny"
