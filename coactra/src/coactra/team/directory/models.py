"""Directory entities.

SQLModel-backed persistence rows load lazily so ``coactra.team.directory`` imports without
``coactra[team]``. Accessing a table model without the extra raises
``MissingExtraError``.
"""

from __future__ import annotations

from typing import Any

_SQL_EXPORTS = frozenset(
    {
        "org_metadata",
        "org_registry",
        "OrgModel",
        "MemberKind",
        "Tenant",
        "Department",
        "Seat",
        "MemberStatus",
        "Member",
        "Membership",
        "ReportingEdge",
        "EscalationRoute",
        "PolicyRef",
        "NodeGrant",
        "MemberOverride",
    }
)


def __getattr__(name: str) -> Any:
    if name not in _SQL_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from coactra.team.directory import _sql_models as sql_models

    return getattr(sql_models, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | _SQL_EXPORTS)
