"""SQLModel-backed directory persistence rows (requires coactra[organization])."""

from __future__ import annotations

from enum import Enum

try:
    from sqlalchemy import Column, JSON, MetaData
    from sqlalchemy.orm import registry as _Registry
    from sqlmodel import Field, SQLModel
except ImportError as exc:  # pragma: no cover - base install gate
    from coactra.errors import MissingExtraError

    raise MissingExtraError(
        "directory SQLModel entities require coactra[organization]; "
        "install with: pip install coactra[organization]"
    ) from exc

# Private MetaData / registry for this library's tables.
#
# WHY: SQLModel's default ``SQLModel.metadata`` is a process-global singleton shared
# by EVERY SQLModel table in the interpreter — including a host application's own
# tables (homelab-mcp also uses SQLModel). Registering our ``table=True`` classes
# there means a second registration of the same table name (a re-import under a
# different module identity, or a host app that also defines a ``tenant`` / ``member``
# / ``department`` table) raises ``InvalidRequestError: Table '…' is already defined
# for this MetaData instance``. Isolating our tables in their OWN MetaData makes the
# library safe to instantiate any number of times in one process and impossible to
# collide with unrelated host tables. ``engine.py`` must call ``create_all`` on THIS
# metadata (not ``SQLModel.metadata``) for the tables to be created.
org_metadata = MetaData()
org_registry = _Registry(metadata=org_metadata)


class OrgModel(SQLModel, registry=org_registry):
    """Base for every directory table — binds them to the library-private metadata."""

    metadata = org_metadata


class MemberKind(str, Enum):
    human = "human"
    service = "service"
    agent = "agent"


class Tenant(OrgModel, table=True):
    """An isolated fleet. Everything below it is scoped by tenant_id."""

    tenant_id: str = Field(primary_key=True)
    name: str = ""


class Department(OrgModel, table=True):
    """An OU node in the org tree — the persistence row for a domain ``Organization``.

    ``parent_id`` makes the tree (None => a tenant-root node); ``block_inheritance`` is
    the AD "Block Inheritance" flag carried per node. Both default to the flat-baseline
    values, so pre-tree callers are unaffected (additive).
    """

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    name: str
    parent_id: int | None = Field(default=None, index=True)
    block_inheritance: bool = False


class Seat(OrgModel, table=True):
    """A role/seat — WHAT a member does. 'domain' is the optional ownership hint
    used to answer 'who owns this?'. ``permissions`` is the role's permission set,
    persisted as a JSON-encoded list of action tokens (empty by default)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    role: str
    domain: str | None = None
    permissions: list[str] = Field(default_factory=list, sa_column=Column(JSON))


class MemberStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    archived = "archived"


class Member(OrgModel, table=True):
    """A human / service / agent that occupies seats within one tenant.

    ``status`` is the lifecycle flag (active vs suspended); it defaults to active so the
    flat-fleet baseline is unchanged (additive).
    """

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    name: str
    kind: MemberKind = MemberKind.agent
    status: MemberStatus = MemberStatus.active
    seniority: int = 0
    created_by: str | None = None
    approved_by: str | None = None


class Membership(OrgModel, table=True):
    """Member ↔ node/seat placement. ``seat_id`` is OPTIONAL — a principal may sit on a
    node without holding a role (a seatless placement). ``department_id`` is OPTIONAL too
    (flat fleet = None)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    member_id: int
    seat_id: int | None = None
    department_id: int | None = None


class ReportingEdge(OrgModel, table=True):
    """A 'reports_to' edge between two seats — the chain of command (optional)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    seat_id: int          # the subordinate seat
    reports_to_seat_id: int  # the seat it escalates to


class EscalationRoute(OrgModel, table=True):
    """An explicit override route: from a seat to a named decider, bypassing the
    reporting chain. Used when escalation should NOT follow the org tree."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    from_seat_id: int
    to_seat_id: int


class PolicyRef(OrgModel, table=True):
    """A versioned REFERENCE to a policy (not the policy engine). 'target' points at
    whatever consumes it; (tenant_id, name, version) identifies a version."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    name: str
    version: int = 1
    target: str = ""


class NodeGrant(OrgModel, table=True):
    """A node-level permission grant — an action conferred at one OU node, inherited
    down the tree (subject to block_inheritance). One row per (node, action)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    node_id: int = Field(index=True, foreign_key="department.id")
    action: str


class MemberOverride(OrgModel, table=True):
    """A per-member explicit allow/deny on a single action (deny beats allow). One row
    per (member, action). The AD explicit-ACE analogue that wins over inheritance."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    member_id: int = Field(index=True, foreign_key="member.id")
    action: str
    effect: str  # "allow" | "deny"
