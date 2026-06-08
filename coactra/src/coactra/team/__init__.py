"""coactra.team - agent rosters plus lazy team directory control-plane APIs."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from coactra.team.facade import Team

_DIRECTORY_EXPORTS = [
    "__version__",
    "MemberKind",
    "Tenant",
    "Department",
    "Seat",
    "Member",
    "Membership",
    "ReportingEdge",
    "EscalationRoute",
    "PolicyRef",
    "OrgStore",
    "Directory",
    "SqliteOrgStore",
    "AsyncOrgStore",
    "AsyncPostgresOrgStore",
    "TenantOrgStoreRouter",
    "make_engine",
    "Organization",
    "Action",
    "Effect",
    "PermissionSet",
    "PolicyReference",
    "make_org_store",
    "make_async_org_store",
    "load_org",
    "save_org",
    "CrossTenantError",
    "MissingExtraError",
    "AuthorizationRequest",
    "AuthorizationDecision",
    "AuthorizationDenied",
    "Authorizer",
    "InMemoryAuthorizer",
    "OpenFGAAuthorizer",
    "require_authorized",
    "AgentSpec",
    "CompanyBootstrapReport",
    "CompanySpec",
    "DepartmentSpec",
    "RoleSpec",
    "SeniorityLevelSpec",
    "bootstrap_company",
    "department_order",
    "preview_company",
    "seniority_rank",
]
__all__ = ["Team", *_DIRECTORY_EXPORTS]


def __getattr__(name: str) -> Any:
    if name == "Team":
        return Team
    if name in _DIRECTORY_EXPORTS:
        return getattr(import_module("coactra.team.directory"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
