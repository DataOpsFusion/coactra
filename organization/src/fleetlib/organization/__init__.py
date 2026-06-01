"""fleetlib.organization — a multi-tenant fleet directory.

Models WHO belongs to which tenant, what seat they hold, who reports to whom, and
WHERE an escalation goes. It answers "who owns this?" and "where does escalation go?"
— nothing else. There is NO workflow execution here: escalate() is a routing query
that returns the next decider, it never runs or owns a work order.
"""

from fleetlib.organization.engine import make_engine
from fleetlib.organization.errors import CrossTenantError
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
from fleetlib.organization.sqlite_store import SqliteOrgStore
from fleetlib.organization.store import OrgStore

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
    "SqliteOrgStore",
    "CrossTenantError",
    "make_engine",
]

__version__ = "0.1.0"
