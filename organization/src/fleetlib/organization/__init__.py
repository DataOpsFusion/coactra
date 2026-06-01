"""fleetlib.organization — a multi-tenant, OU-tree org model (AD-inspired).

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

from fleetlib.organization.domain import (
    Action,
    Effect,
    Organization,
    PermissionSet,
)
from fleetlib.organization.engine import make_engine
from fleetlib.organization.errors import CrossTenantError, MissingExtraError
from fleetlib.organization.factory import make_org_store
from fleetlib.organization.models import (
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
from fleetlib.organization.repository import Directory, Neo4jOrgStore, OrgStore, SqliteOrgStore
from fleetlib.organization.service import load_org, save_org

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
    "Neo4jOrgStore",
    "make_engine",
    # domain model (v0.2)
    "Organization",
    "Action",
    "Effect",
    "PermissionSet",
    # factory + service (DI composition root + explicit persistence)
    "make_org_store",
    "load_org",
    "save_org",
    # errors
    "CrossTenantError",
    "MissingExtraError",
]

__version__ = "0.2.0"
