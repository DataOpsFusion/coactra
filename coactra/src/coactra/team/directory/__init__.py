"""coactra.team.directory - team directory persistence and authority model.

The package initializer stays dependency-light. SQL and optional authorization
backends are imported lazily when their exported names are accessed.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from coactra._version import distribution_version

__all__ = [
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
    "TenantOrgStoreRouter",
    "make_engine",
    "Organization",
    "Action",
    "Effect",
    "PermissionSet",
    "PolicyReference",
    "make_org_store",
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

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "MemberKind": ("coactra.team.directory.models", "MemberKind"),
    "Tenant": ("coactra.team.directory.models", "Tenant"),
    "Department": ("coactra.team.directory.models", "Department"),
    "Seat": ("coactra.team.directory.models", "Seat"),
    "Member": ("coactra.team.directory.models", "Member"),
    "Membership": ("coactra.team.directory.models", "Membership"),
    "ReportingEdge": ("coactra.team.directory.models", "ReportingEdge"),
    "EscalationRoute": ("coactra.team.directory.models", "EscalationRoute"),
    "PolicyRef": ("coactra.team.directory.models", "PolicyRef"),
    "OrgStore": ("coactra.team.directory.repository", "OrgStore"),
    "Directory": ("coactra.team.directory.repository", "Directory"),
    "SqliteOrgStore": ("coactra.team.directory.repository", "SqliteOrgStore"),
    "TenantOrgStoreRouter": ("coactra.team.directory.repository", "TenantOrgStoreRouter"),
    "make_engine": ("coactra.team.directory.engine", "make_engine"),
    "Organization": ("coactra.team.directory.domain", "Organization"),
    "Action": ("coactra.team.directory.domain", "Action"),
    "Effect": ("coactra.team.directory.domain", "Effect"),
    "PermissionSet": ("coactra.team.directory.domain", "PermissionSet"),
    "PolicyReference": ("coactra.team.directory.domain", "PolicyReference"),
    "make_org_store": ("coactra.team.directory.factory", "make_org_store"),
    "load_org": ("coactra.team.directory.service", "load_org"),
    "save_org": ("coactra.team.directory.service", "save_org"),
    "CrossTenantError": ("coactra.team.directory.errors", "CrossTenantError"),
    "MissingExtraError": ("coactra.team.directory.errors", "MissingExtraError"),
    "AuthorizationRequest": ("coactra.team.directory.authorization", "AuthorizationRequest"),
    "AuthorizationDecision": ("coactra.team.directory.authorization", "AuthorizationDecision"),
    "AuthorizationDenied": ("coactra.team.directory.authorization", "AuthorizationDenied"),
    "Authorizer": ("coactra.team.directory.authorization", "Authorizer"),
    "InMemoryAuthorizer": ("coactra.team.directory.authorization", "InMemoryAuthorizer"),
    "OpenFGAAuthorizer": ("coactra.team.directory.adapters.openfga", "OpenFGAAuthorizer"),
    "require_authorized": ("coactra.team.directory.authorization", "require_authorized"),
    "AgentSpec": ("coactra.team.directory.company", "AgentSpec"),
    "CompanyBootstrapReport": ("coactra.team.directory.company", "CompanyBootstrapReport"),
    "CompanySpec": ("coactra.team.directory.company", "CompanySpec"),
    "DepartmentSpec": ("coactra.team.directory.company", "DepartmentSpec"),
    "RoleSpec": ("coactra.team.directory.company", "RoleSpec"),
    "SeniorityLevelSpec": ("coactra.team.directory.company", "SeniorityLevelSpec"),
    "bootstrap_company": ("coactra.team.directory.company", "bootstrap_company"),
    "department_order": ("coactra.team.directory.company", "department_order"),
    "preview_company": ("coactra.team.directory.company", "preview_company"),
    "seniority_rank": ("coactra.team.directory.company", "seniority_rank"),
}


def __getattr__(name: str) -> Any:
    if name == "__version__":
        return distribution_version()
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    return getattr(import_module(module_name), attr_name)


def __dir__() -> list[str]:
    return sorted(__all__)


__version__ = distribution_version()
