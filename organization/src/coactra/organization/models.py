"""Directory entities.

These SQLModel classes are BOTH the ORM tables (table=True) AND the plain pydantic
objects the OrgStore Protocol passes and returns — one model layer, no DTO split.
tenant_id is on EVERY entity; it is the multi-tenant key threaded through the whole
API. Flat-fleet is the baseline: a Member + a Seat is enough. Department + reporting
edges are optional and additive — hierarchy is first-class but never required.
"""

from __future__ import annotations

from enum import Enum

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel


class MemberKind(str, Enum):
    human = "human"
    service = "service"
    agent = "agent"


class Tenant(SQLModel, table=True):
    """An isolated fleet. Everything below it is scoped by tenant_id."""

    tenant_id: str = Field(primary_key=True)
    name: str = ""


class Department(SQLModel, table=True):
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


class Seat(SQLModel, table=True):
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


class Member(SQLModel, table=True):
    """A human / service / agent that occupies seats within one tenant.

    ``status`` is the lifecycle flag (active vs suspended); it defaults to active so the
    flat-fleet baseline is unchanged (additive).
    """

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    name: str
    kind: MemberKind = MemberKind.agent
    status: MemberStatus = MemberStatus.active


class Membership(SQLModel, table=True):
    """Member ↔ node/seat placement. ``seat_id`` is OPTIONAL — a principal may sit on a
    node without holding a role (a seatless placement). ``department_id`` is OPTIONAL too
    (flat fleet = None)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    member_id: int
    seat_id: int | None = None
    department_id: int | None = None


class ReportingEdge(SQLModel, table=True):
    """A 'reports_to' edge between two seats — the chain of command (optional)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    seat_id: int          # the subordinate seat
    reports_to_seat_id: int  # the seat it escalates to


class EscalationRoute(SQLModel, table=True):
    """An explicit override route: from a seat to a named decider, bypassing the
    reporting chain. Used when escalation should NOT follow the org tree."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    from_seat_id: int
    to_seat_id: int


class PolicyRef(SQLModel, table=True):
    """A versioned REFERENCE to a policy (not the policy engine). 'target' points at
    whatever consumes it; (tenant_id, name, version) identifies a version."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    name: str
    version: int = 1
    target: str = ""


class NodeGrant(SQLModel, table=True):
    """A node-level permission grant — an action conferred at one OU node, inherited
    down the tree (subject to block_inheritance). One row per (node, action)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    node_id: int = Field(index=True, foreign_key="department.id")
    action: str


class MemberOverride(SQLModel, table=True):
    """A per-member explicit allow/deny on a single action (deny beats allow). One row
    per (member, action). The AD explicit-ACE analogue that wins over inheritance."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    member_id: int = Field(index=True, foreign_key="member.id")
    action: str
    effect: str  # "allow" | "deny"
