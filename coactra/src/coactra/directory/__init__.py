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
from coactra.directory.engine import make_engine
from coactra.directory.errors import CrossTenantError, MissingExtraError
from coactra.directory.factory import make_async_org_store, make_org_store
from coactra.directory.models import (
    Department,
    EscalationRoute,
    Member,
    MemberKind,
    Membership,
    PolicyRef,
    ReportingEdge,
    Seat,
    Tenant,
)
from coactra.directory.repository import (
    AsyncOrgStore,
    AsyncPostgresOrgStore,
    Directory,
    OrgStore,
    SqliteOrgStore,
    TenantOrgStoreRouter,
)
from coactra.directory.service import load_org, save_org

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

__version__ = "0.2.0"
