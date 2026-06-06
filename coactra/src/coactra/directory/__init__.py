"""coactra.directory — a multi-tenant, OU-tree org model (AD-inspired).

A composable, multi-tenant org **tree** with real behavior: the ``Organization``
aggregate is a composite OU node (parent + children) holding member principals and
node-level permission grants, with AD-style permission **inheritance** (per-node
``block_inheritance`` + per-member overrides). It owns **structure, authority,
lifecycle, and permissions** — and nothing else: no workflow execution, no messaging,
no infra provisioning.

Persistence is the repository pattern with explicit ``save_org``/``load_org``: the
in-memory tree is mutated, then flushed through an injected ``OrgStore`` (selected by
``make_org_store``). The legacy directory write/read API (tenants/seats/members/
reporting/escalation/ownership/policy-refs) is preserved alongside the new model.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from coactra._version import distribution_version

from coactra.directory.adapters import OpenFGAAuthorizer
from coactra.directory.authorization import (
    AuthorizationDecision,
    AuthorizationDenied,
    AuthorizationRequest,
    Authorizer,
    InMemoryAuthorizer,
    require_authorized,
)
from coactra.directory.company import (
    AgentSpec,
    CompanyBootstrapReport,
    CompanySpec,
    DepartmentSpec,
    RoleSpec,
    SeniorityLevelSpec,
    bootstrap_company,
    department_order,
    preview_company,
    seniority_rank,
)
from coactra.directory.domain import (
    Action,
    Effect,
    Organization,
    PolicyReference,
    PermissionSet,
)
from coactra.directory.errors import CrossTenantError, MissingExtraError

__all__ = [
    "__version__",
    # legacy directory entities (SQLModel rows) — unchanged public surface
    "MemberKind",
    "Tenant",
    "Department",
    "Seat",
    "Member",
    "Membership",
    "ReportingEdge",
    "EscalationRoute",
    "PolicyRef",
    # repository SPI + backends
    "OrgStore",
    "Directory",
    "SqliteOrgStore",
    "AsyncOrgStore",
    "AsyncPostgresOrgStore",
    "TenantOrgStoreRouter",
    "make_engine",
    # domain model (v0.2)
    "Organization",
    "Action",
    "Effect",
    "PermissionSet",
    "PolicyReference",
    # factory + service (DI composition root + explicit persistence)
    "make_org_store",
    "make_async_org_store",
    "load_org",
    "save_org",
    # errors
    "CrossTenantError",
    "MissingExtraError",
    # optional external authorization bridge
    "AuthorizationRequest",
    "AuthorizationDecision",
    "AuthorizationDenied",
    "Authorizer",
    "InMemoryAuthorizer",
    "OpenFGAAuthorizer",
    "require_authorized",
    # company control-plane primitives
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
    # SQLModel entities
    "MemberKind": ("coactra.directory.models", "MemberKind"),
    "Tenant": ("coactra.directory.models", "Tenant"),
    "Department": ("coactra.directory.models", "Department"),
    "Seat": ("coactra.directory.models", "Seat"),
    "Member": ("coactra.directory.models", "Member"),
    "Membership": ("coactra.directory.models", "Membership"),
    "ReportingEdge": ("coactra.directory.models", "ReportingEdge"),
    "EscalationRoute": ("coactra.directory.models", "EscalationRoute"),
    "PolicyRef": ("coactra.directory.models", "PolicyRef"),
    # persistence SPI + backends
    "OrgStore": ("coactra.directory.repository", "OrgStore"),
    "Directory": ("coactra.directory.repository", "Directory"),
    "SqliteOrgStore": ("coactra.directory.repository", "SqliteOrgStore"),
    "AsyncOrgStore": ("coactra.directory.repository", "AsyncOrgStore"),
    "AsyncPostgresOrgStore": ("coactra.directory.repository", "AsyncPostgresOrgStore"),
    "TenantOrgStoreRouter": ("coactra.directory.repository", "TenantOrgStoreRouter"),
    "make_engine": ("coactra.directory.engine", "make_engine"),
    # factory + service
    "make_org_store": ("coactra.directory.factory", "make_org_store"),
    "make_async_org_store": ("coactra.directory.factory", "make_async_org_store"),
    "load_org": ("coactra.directory.service", "load_org"),
    "save_org": ("coactra.directory.service", "save_org"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    return getattr(import_module(module_name), attr_name)


__version__ = distribution_version()
