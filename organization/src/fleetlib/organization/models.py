"""Directory entities.

These SQLModel classes are BOTH the ORM tables (table=True) AND the plain pydantic
objects the OrgStore Protocol passes and returns — one model layer, no DTO split.
tenant_id is on EVERY entity; it is the multi-tenant key threaded through the whole
API. Flat-fleet is the baseline: a Member + a Seat is enough. Department + reporting
edges are optional and additive — hierarchy is first-class but never required.
"""

from __future__ import annotations

from enum import Enum

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
    """Optional grouping inside a tenant — a 'dedicated space' (e.g. a standing R&D group)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    name: str


class Seat(SQLModel, table=True):
    """A role/seat — WHAT a member does. 'domain' is the optional ownership hint
    used to answer 'who owns this?'."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    role: str
    domain: str | None = None


class Member(SQLModel, table=True):
    """A human / service / agent that occupies seats within one tenant."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    name: str
    kind: MemberKind = MemberKind.agent


class Membership(SQLModel, table=True):
    """Member ↔ Seat assignment. department_id is OPTIONAL (flat fleet = None)."""

    id: int | None = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, foreign_key="tenant.tenant_id")
    member_id: int
    seat_id: int
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
