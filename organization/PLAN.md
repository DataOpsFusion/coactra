# fleetlib.organization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a publishable, multi-tenant **fleet directory** — a standalone model of *who belongs to which tenant*, *what seat they hold*, *who reports to whom*, and *where an escalation goes* — over an `OrgStore` Protocol with ONE working default (`SqliteOrgStore`, SQLite via sqlmodel, in-memory for tests). It answers **"who owns this?"** and **"where does escalation go?"** and nothing else. There is **no workflow execution inside organization**: `escalate()` is a routing *query* that returns the next decider up the chain — it never runs, mutates, or owns a work order.

**Architecture:** A thin tenant-scoped directory, not an execution engine. An `OrgStore` `typing.Protocol` defines the contract; every method takes `tenant_id` as its first argument and isolation is enforced by `WHERE tenant_id = ?` filter-discipline (not structural — see the dedicated isolation task). The SQLModel entity classes (Tenant, Department, Seat, Member, Membership, ReportingEdge, EscalationRoute, PolicyRef) are *both* the ORM tables (`table=True`) AND the plain pydantic objects the Protocol passes and returns — one model layer, no DTO/ORM split. The ONE working default `SqliteOrgStore` wraps a sqlmodel engine built with `StaticPool` (so an in-memory DB survives across sessions in tests). Flat fleet is the baseline: a Member exists in a tenant with just a Seat — `department_id` and reporting edges are **optional and additive**. Hierarchy (departments + reporting edges) is first-class but never required. A single Neo4j adapter **stub** (reporting edges are graph-shaped) demonstrates the swap and raises `MissingExtraError` until its extra lands — sqlmodel→Postgres is just a URL change, so we do not manufacture extra stubs.

**Tech Stack:** Python 3.12+, sqlmodel (>=0.0.21, brings pydantic v2 + SQLAlchemy), pydantic v2, hatchling (PEP 420 namespace package, src layout), pytest. Default store = SQLite (in-memory `sqlite://` + `StaticPool` for tests, file URL for prod). Optional extras: `neo4j` (stub only), `dev`. NO workflow execution — this is a directory that answers ownership and escalation-routing questions.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `pyproject.toml` | Distribution `fleetlib-organization`; hatchling targets the `fleetlib` namespace dir; runtime deps `sqlmodel`, `pydantic`; `[project.optional-dependencies]` for `neo4j`/`dev`. |
| `src/fleetlib/organization/__init__.py` | Public API surface — re-exports `MemberKind`, `Tenant`, `Department`, `Seat`, `Member`, `Membership`, `ReportingEdge`, `EscalationRoute`, `PolicyRef`, `OrgStore`, `SqliteOrgStore`, `CrossTenantError`, `make_engine`. NO `src/fleetlib/__init__.py` (namespace package). |
| `src/fleetlib/organization/py.typed` | PEP 561 typing marker. |
| `src/fleetlib/organization/models.py` | All SQLModel entities (`table=True`) — they double as the pydantic objects the Protocol passes/returns. `MemberKind` enum (human/service/agent). |
| `src/fleetlib/organization/errors.py` | `CrossTenantError` (raised when an operation would span two tenants) + `MissingExtraError`. |
| `src/fleetlib/organization/engine.py` | `make_engine(url="sqlite://")` — builds a sqlmodel engine with `StaticPool` + `check_same_thread=False`, runs `create_all`. The StaticPool detail is what keeps an in-memory DB alive across sessions. |
| `src/fleetlib/organization/store.py` | `OrgStore` `typing.Protocol` — the tenant-scoped directory contract (every method takes `tenant_id` first). |
| `src/fleetlib/organization/sqlite_store.py` | `SqliteOrgStore` — the ONE working default. Tenant/department/seat/member/membership CRUD, reporting edges, `escalate()` routing query, ownership lookup, policy-ref versioning. Every read filters by `tenant_id`; every cross-tenant write raises `CrossTenantError`. |
| `src/fleetlib/organization/adapters/__init__.py` | Adapters subpackage marker. |
| `src/fleetlib/organization/adapters/neo4j.py` | `Neo4jOrgStore` stub — graph-shaped backend; raises `MissingExtraError` until the `neo4j` extra + real impl land. |
| `tests/conftest.py` | `store` fixture — a fresh in-memory `SqliteOrgStore` per test. |
| `tests/test_packaging.py` | Asserts `import fleetlib.organization` works and `fleetlib` is a PEP 420 namespace package. |
| `tests/test_engine.py` | `make_engine` write-then-read-in-a-new-session survives (proves StaticPool). |
| `tests/test_models.py` | Entity construction, `MemberKind` values, optional `department_id` defaults to None. |
| `tests/test_tenants_members.py` | Create tenant, add member with a seat, list — the flat-fleet baseline (zero departments, zero edges). |
| `tests/test_isolation.py` | Cross-tenant reads return nothing; cross-tenant membership/edge **raises** `CrossTenantError`. The core invariant. |
| `tests/test_hierarchy.py` | Departments + reporting edges (`reports_to`); the optional-but-first-class hierarchy. |
| `tests/test_escalation.py` | `escalate()` returns the next decider up one tier and `resolve_decider()` walks to the top — neither executes anything. |
| `tests/test_ownership.py` | `owner_of()` answers "who owns this?" for a resource within a tenant. |
| `tests/test_policy_refs.py` | Versioned policy references — current vs specific version. |
| `tests/test_adapter_stub.py` | Neo4j stub raises `MissingExtraError` on use. |
| `tests/test_public_api.py` | Locks the public surface + an end-to-end directory walkthrough. |

---

## Task 1: Package scaffold (namespace package + importable)

**Files:**
- Create: `pyproject.toml`
- Create: `src/fleetlib/organization/__init__.py`
- Create: `src/fleetlib/organization/py.typed`
- Test: `tests/test_packaging.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_packaging.py
import importlib


def test_organization_imports():
    mod = importlib.import_module("fleetlib.organization")
    assert mod is not None


def test_fleetlib_is_namespace_package():
    import fleetlib

    # PEP 420 namespace packages have no __file__ and expose a virtual __path__.
    assert getattr(fleetlib, "__file__", None) is None
    assert hasattr(fleetlib, "__path__")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_packaging.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fleetlib'`

- [ ] **Step 3: Write minimal implementation**

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "fleetlib-organization"
version = "0.1.0"
description = "Multi-tenant fleet directory for AI agents — tenants, seats, memberships, reporting + escalation routing. No workflow execution."
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
dependencies = ["sqlmodel>=0.0.21", "pydantic>=2.7"]

[project.optional-dependencies]
neo4j = ["neo4j>=5"]
dev = ["pytest>=8"]

[tool.hatch.build.targets.wheel]
# PEP 420 namespace: ship the fleetlib/ dir WITHOUT a top-level fleetlib/__init__.py
packages = ["src/fleetlib"]

[tool.hatch.build.targets.sdist]
include = ["src/fleetlib", "README.md", "tests"]
```

```python
# src/fleetlib/organization/__init__.py
"""fleetlib.organization — a multi-tenant fleet directory.

Models WHO belongs to which tenant, what seat they hold, who reports to whom, and
WHERE an escalation goes. It answers "who owns this?" and "where does escalation go?"
— nothing else. There is NO workflow execution here: escalate() is a routing query
that returns the next decider, it never runs or owns a work order.
"""

__all__ = [
    "__version__",
]

__version__ = "0.1.0"
```

```text
# src/fleetlib/organization/py.typed
```

(Do NOT create `src/fleetlib/__init__.py` — its absence is what makes `fleetlib` a namespace package.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pip install -e . && pytest tests/test_packaging.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/fleetlib/organization/__init__.py src/fleetlib/organization/py.typed tests/test_packaging.py
git commit -m "feat(organization): namespace package scaffold + importable surface"
```

---

## Task 2: Errors — cross-tenant guard + missing-extra

**Files:**
- Create: `src/fleetlib/organization/errors.py`
- Modify: `src/fleetlib/organization/__init__.py`
- Test: folded into later tasks (no standalone test; exercised by isolation + stub tests)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_errors.py
from fleetlib.organization import CrossTenantError
from fleetlib.organization.errors import MissingExtraError


def test_cross_tenant_error_is_value_error():
    # Callers may catch it as ValueError; it is a precise, named isolation breach.
    assert issubclass(CrossTenantError, ValueError)


def test_missing_extra_error_is_runtime_error():
    assert issubclass(MissingExtraError, RuntimeError)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_errors.py -v`
Expected: FAIL with `ImportError: cannot import name 'CrossTenantError'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/errors.py
"""Organization errors.

CrossTenantError  — raised when an operation would link or read across a tenant
                    boundary. Isolation is the core invariant; a breach is loud.
MissingExtraError — raised when an optional-extra backend is used before its extra
                    (and a real implementation) exist.
"""

from __future__ import annotations


class CrossTenantError(ValueError):
    """An operation tried to span two tenants. Multi-tenant isolation forbids it."""


class MissingExtraError(RuntimeError):
    """An optional-extra backend was used before its extra/impl exist."""
```

```python
# src/fleetlib/organization/__init__.py  (extend imports + __all__)
from fleetlib.organization.errors import CrossTenantError

__all__ = [
    "__version__",
    "CrossTenantError",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_errors.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/errors.py src/fleetlib/organization/__init__.py tests/test_errors.py
git commit -m "feat(organization): CrossTenantError + MissingExtraError"
```

---

## Task 3: Models — the directory entities (flat-fleet first)

**Files:**
- Create: `src/fleetlib/organization/models.py`
- Modify: `src/fleetlib/organization/__init__.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from fleetlib.organization import (
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


def test_member_kind_values():
    assert {k.value for k in MemberKind} == {"human", "service", "agent"}


def test_flat_member_needs_no_department():
    # Baseline fleet shape: a member exists in a tenant with just a kind/name.
    m = Member(tenant_id="acme", name="alice", kind=MemberKind.human)
    assert m.tenant_id == "acme"
    assert m.kind is MemberKind.human


def test_membership_department_is_optional():
    ms = Membership(tenant_id="acme", member_id=1, seat_id=2)
    assert ms.department_id is None  # hierarchy is additive, never required


def test_entities_carry_tenant_id():
    for cls in (Tenant, Department, Seat, Member, Membership, ReportingEdge, EscalationRoute, PolicyRef):
        assert "tenant_id" in cls.model_fields


def test_seat_has_role_and_optional_domain():
    s = Seat(tenant_id="acme", role="platform", domain="infrastructure")
    assert s.role == "platform"
    assert s.domain == "infrastructure"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'Department'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/models.py
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
```

```python
# src/fleetlib/organization/__init__.py  (extend imports + __all__)
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

__all__ = [
    "__version__",
    "CrossTenantError",
    "MemberKind",
    "Tenant",
    "Department",
    "Seat",
    "Member",
    "Membership",
    "ReportingEdge",
    "EscalationRoute",
    "PolicyRef",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/models.py src/fleetlib/organization/__init__.py tests/test_models.py
git commit -m "feat(organization): directory entities (tenant/dept/seat/member/membership/edges/policy)"
```

---

## Task 4: Engine factory — StaticPool keeps in-memory SQLite alive

**Files:**
- Create: `src/fleetlib/organization/engine.py`
- Modify: `src/fleetlib/organization/__init__.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine.py
from sqlmodel import Session, select

from fleetlib.organization import Tenant, make_engine


def test_write_then_read_in_a_new_session_survives():
    # The StaticPool landmine: a plain sqlite:// in-memory engine gives a fresh DB per
    # connection, so a write in one session vanishes in the next. StaticPool fixes it.
    engine = make_engine()  # defaults to in-memory sqlite://
    with Session(engine) as s:
        s.add(Tenant(tenant_id="acme", name="Acme"))
        s.commit()

    with Session(engine) as s:  # brand-new session / connection
        rows = s.exec(select(Tenant)).all()
    assert [t.tenant_id for t in rows] == ["acme"]


def test_tables_are_created_on_make_engine():
    engine = make_engine()
    with Session(engine) as s:
        # No error => the 'tenant' table exists.
        assert s.exec(select(Tenant)).all() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_engine.py -v`
Expected: FAIL with `ImportError: cannot import name 'make_engine'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/engine.py
"""Engine factory.

make_engine() builds a sqlmodel engine and creates all tables. For the in-memory
sqlite:// default it uses StaticPool + check_same_thread=False so the SAME in-memory
database is reused across every session/connection — without StaticPool, each new
connection gets a fresh empty DB and writes appear to vanish. File URLs work too.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

# Importing models registers every table on SQLModel.metadata before create_all().
from fleetlib.organization import models as _models  # noqa: F401


def make_engine(url: str = "sqlite://") -> Engine:
    connect_args = {}
    kwargs: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, connect_args=connect_args, **kwargs)
    SQLModel.metadata.create_all(engine)
    return engine
```

```python
# src/fleetlib/organization/__init__.py  (extend imports + __all__)
from fleetlib.organization.engine import make_engine

# ...add "make_engine" to __all__ (place after the entity names)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_engine.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/engine.py src/fleetlib/organization/__init__.py tests/test_engine.py
git commit -m "feat(organization): make_engine — StaticPool in-memory SQLite + create_all"
```

---

## Task 5: OrgStore Protocol — the tenant-scoped directory contract

**Files:**
- Create: `src/fleetlib/organization/store.py`
- Modify: `src/fleetlib/organization/__init__.py`
- Test: `tests/test_store_protocol.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_store_protocol.py
from fleetlib.organization import (
    Department,
    Member,
    OrgStore,
    PolicyRef,
    Seat,
    Tenant,
)


class _Dummy:
    """A no-op class that implements the FULL OrgStore surface — proves the
    Protocol's method set is exactly the swap contract a backend must satisfy."""

    def add_tenant(self, tenant: Tenant) -> Tenant:
        return tenant

    def add_seat(self, tenant_id: str, seat: Seat) -> Seat:
        return seat

    def add_member(self, tenant_id: str, member: Member) -> Member:
        return member

    def assign(self, tenant_id, member_id, seat_id, department_id=None) -> None:
        ...

    def members(self, tenant_id: str) -> list[Member]:
        return []

    def add_department(self, tenant_id: str, department: Department) -> Department:
        return department

    def reports_to(self, tenant_id, seat_id, reports_to_seat_id) -> None:
        ...

    def manager_of(self, tenant_id: str, seat_id: int):
        return None

    def set_escalation_route(self, tenant_id, from_seat_id, to_seat_id) -> None:
        ...

    def escalate(self, tenant_id: str, seat_id: int):
        return None

    def owner_of(self, tenant_id: str, resource_domain: str):
        return None

    def add_policy_ref(self, tenant_id: str, policy_ref: PolicyRef) -> PolicyRef:
        return policy_ref

    def policy_ref(self, tenant_id: str, name: str, version: int | None = None):
        return None


def test_protocol_is_runtime_checkable():
    assert isinstance(_Dummy(), OrgStore)


def test_incomplete_class_is_not_a_store():
    class Partial:
        def members(self, tenant_id):
            return []

    assert not isinstance(Partial(), OrgStore)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_store_protocol.py -v`
Expected: FAIL with `ImportError: cannot import name 'OrgStore'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/store.py
"""OrgStore — the swappable directory SPI.

Every method takes tenant_id (or a tenant-bearing entity) FIRST; multi-tenant scoping
is part of the contract, not the caller's discipline alone. The default SqliteOrgStore
is the ONE working implementation; the Neo4j adapter is an optional-extra stub. This
contract is a DIRECTORY — it answers ownership and escalation-routing questions. It does
NOT run, mutate, or own work orders.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fleetlib.organization.models import Department, Member, PolicyRef, Seat, Tenant


@runtime_checkable
class OrgStore(Protocol):
    # --- tenants / seats / members / assignment (flat-fleet baseline) ----------

    def add_tenant(self, tenant: Tenant) -> Tenant:
        """Register a tenant (isolation root)."""
        ...

    def add_seat(self, tenant_id: str, seat: Seat) -> Seat:
        """Create a role/seat within a tenant."""
        ...

    def add_member(self, tenant_id: str, member: Member) -> Member:
        """Add a human/service/agent member within a tenant."""
        ...

    def assign(
        self,
        tenant_id: str,
        member_id: int,
        seat_id: int,
        department_id: int | None = None,
    ) -> None:
        """Assign a member to a seat (department optional => flat fleet)."""
        ...

    def members(self, tenant_id: str) -> list[Member]:
        """List a tenant's members (never another tenant's)."""
        ...

    # --- hierarchy: departments + reporting edges (optional, first-class) ------

    def add_department(self, tenant_id: str, department: Department) -> Department:
        """Create a department (optional grouping inside a tenant)."""
        ...

    def reports_to(self, tenant_id: str, seat_id: int, reports_to_seat_id: int) -> None:
        """Record a reporting edge — the chain of command (optional hierarchy)."""
        ...

    def manager_of(self, tenant_id: str, seat_id: int) -> Seat | None:
        """The seat one reporting tier up (None at the top / flat fleet)."""
        ...

    # --- escalation ROUTING (query only — no execution) -----------------------

    def set_escalation_route(
        self, tenant_id: str, from_seat_id: int, to_seat_id: int
    ) -> None:
        """Record an explicit override route that bypasses the reporting chain."""
        ...

    def escalate(self, tenant_id: str, seat_id: int) -> Seat | None:
        """ROUTING QUERY: return the seat one tier up. Never executes anything."""
        ...

    # --- ownership + versioned policy references ------------------------------

    def owner_of(self, tenant_id: str, resource_domain: str) -> Seat | None:
        """Answer 'who owns this?' — the seat whose domain matches the resource."""
        ...

    def add_policy_ref(self, tenant_id: str, policy_ref: PolicyRef) -> PolicyRef:
        """Record a versioned reference to a policy (not a policy engine)."""
        ...

    def policy_ref(
        self, tenant_id: str, name: str, version: int | None = None
    ) -> PolicyRef | None:
        """Current (highest) version, or a specific version if given."""
        ...
```

```python
# src/fleetlib/organization/__init__.py  (extend imports + __all__)
from fleetlib.organization.store import OrgStore

# ...add "OrgStore" to __all__
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_store_protocol.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/store.py src/fleetlib/organization/__init__.py tests/test_store_protocol.py
git commit -m "feat(organization): OrgStore Protocol — tenant-scoped directory contract"
```

---

## Task 6: SqliteOrgStore — tenants, seats, members, assignment (default, part 1)

**Files:**
- Create: `src/fleetlib/organization/sqlite_store.py`
- Create: `tests/conftest.py`
- Modify: `src/fleetlib/organization/__init__.py`
- Test: `tests/test_tenants_members.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/conftest.py
import pytest

from fleetlib.organization import SqliteOrgStore


@pytest.fixture
def store() -> SqliteOrgStore:
    # Fresh in-memory store per test (StaticPool keeps it alive across sessions).
    return SqliteOrgStore()
```

```python
# tests/test_tenants_members.py
from fleetlib.organization import Member, MemberKind, Seat, Tenant


def test_flat_fleet_create_member_with_seat(store):
    store.add_tenant(Tenant(tenant_id="acme", name="Acme"))
    seat = store.add_seat("acme", Seat(tenant_id="acme", role="platform"))
    member = store.add_member("acme", Member(tenant_id="acme", name="alice", kind=MemberKind.agent))
    store.assign("acme", member_id=member.id, seat_id=seat.id)  # no department => flat

    listed = store.members("acme")
    assert [m.name for m in listed] == ["alice"]
    assert seat.id is not None and member.id is not None


def test_add_seat_persists_role_and_domain(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    seat = store.add_seat("acme", Seat(tenant_id="acme", role="dba", domain="database"))
    assert seat.role == "dba"
    assert seat.domain == "database"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tenants_members.py -v`
Expected: FAIL with `ImportError: cannot import name 'SqliteOrgStore'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/sqlite_store.py
"""SqliteOrgStore — the ONE working default OrgStore.

SQLite via sqlmodel. Tenant-isolated by FILTER DISCIPLINE: every read carries a
WHERE tenant_id = ? and every cross-tenant write raises CrossTenantError. In SQL,
isolation is not structural (unlike a dict keyed by tenant) — so the guards here ARE
the invariant. escalate() is a routing query (Task 9); this part covers the CRUD core.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from fleetlib.organization.engine import make_engine
from fleetlib.organization.errors import CrossTenantError
from fleetlib.organization.models import Member, Membership, Seat, Tenant


class SqliteOrgStore:
    """In-memory (default) or file-backed SQLite directory store."""

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine or make_engine()

    def _check(self, tenant_id: str, entity) -> None:
        # A tenant-bearing entity must match the operation's tenant_id, or it's a breach.
        if getattr(entity, "tenant_id", tenant_id) != tenant_id:
            raise CrossTenantError(
                f"entity tenant_id={entity.tenant_id!r} != operation tenant_id={tenant_id!r}"
            )

    def add_tenant(self, tenant: Tenant) -> Tenant:
        with Session(self._engine) as s:
            s.add(tenant)
            s.commit()
            s.refresh(tenant)
            return tenant

    def add_seat(self, tenant_id: str, seat: Seat) -> Seat:
        self._check(tenant_id, seat)
        with Session(self._engine) as s:
            s.add(seat)
            s.commit()
            s.refresh(seat)
            return seat

    def add_member(self, tenant_id: str, member: Member) -> Member:
        self._check(tenant_id, member)
        with Session(self._engine) as s:
            s.add(member)
            s.commit()
            s.refresh(member)
            return member

    def assign(
        self,
        tenant_id: str,
        member_id: int,
        seat_id: int,
        department_id: int | None = None,
    ) -> None:
        # member and seat must both belong to this tenant (Task 8 proves the guard).
        with Session(self._engine) as s:
            member = s.get(Member, member_id)
            seat = s.get(Seat, seat_id)
            for ent in (member, seat):
                if ent is None or ent.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"member_id={member_id}/seat_id={seat_id} not both in tenant {tenant_id!r}"
                    )
            s.add(
                Membership(
                    tenant_id=tenant_id,
                    member_id=member_id,
                    seat_id=seat_id,
                    department_id=department_id,
                )
            )
            s.commit()

    def members(self, tenant_id: str) -> list[Member]:
        with Session(self._engine) as s:
            return list(s.exec(select(Member).where(Member.tenant_id == tenant_id)).all())
```

```python
# src/fleetlib/organization/__init__.py  (extend imports + __all__)
from fleetlib.organization.sqlite_store import SqliteOrgStore

# ...add "SqliteOrgStore" to __all__
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_tenants_members.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/sqlite_store.py tests/conftest.py src/fleetlib/organization/__init__.py tests/test_tenants_members.py
git commit -m "feat(organization): SqliteOrgStore CRUD core — tenants/seats/members/assign (flat fleet)"
```

---

## Task 7: Hierarchy — departments + reporting edges (optional, first-class)

**Files:**
- Modify: `src/fleetlib/organization/sqlite_store.py`
- Test: `tests/test_hierarchy.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hierarchy.py
from fleetlib.organization import Department, Seat, Tenant


def _two_seats(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    junior = store.add_seat("acme", Seat(tenant_id="acme", role="platform"))
    senior = store.add_seat("acme", Seat(tenant_id="acme", role="manager"))
    return junior, senior


def test_reports_to_records_an_edge(store):
    junior, senior = _two_seats(store)
    store.reports_to("acme", seat_id=junior.id, reports_to_seat_id=senior.id)
    # The edge is queryable as the manager of the junior seat.
    assert store.manager_of("acme", junior.id).id == senior.id


def test_seat_without_edge_has_no_manager(store):
    junior, _ = _two_seats(store)
    # Flat fleet: a seat may simply have no one above it.
    assert store.manager_of("acme", junior.id) is None


def test_department_can_be_created_and_used_in_assignment(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    seat = store.add_seat("acme", Seat(tenant_id="acme", role="rnd"))
    from fleetlib.organization import Member, MemberKind

    member = store.add_member("acme", Member(tenant_id="acme", name="bob", kind=MemberKind.agent))
    dept = store.add_department("acme", Department(tenant_id="acme", name="R&D"))
    store.assign("acme", member_id=member.id, seat_id=seat.id, department_id=dept.id)
    assert dept.id is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hierarchy.py -v`
Expected: FAIL with `AttributeError: 'SqliteOrgStore' object has no attribute 'add_department'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/sqlite_store.py  — add imports + methods

# add to the existing import line:
from fleetlib.organization.models import (
    Department,
    Member,
    Membership,
    ReportingEdge,
    Seat,
    Tenant,
)

    # --- hierarchy (optional, first-class) -------------------------------------

    def add_department(self, tenant_id: str, department: Department) -> Department:
        self._check(tenant_id, department)
        with Session(self._engine) as s:
            s.add(department)
            s.commit()
            s.refresh(department)
            return department

    def reports_to(self, tenant_id: str, seat_id: int, reports_to_seat_id: int) -> None:
        with Session(self._engine) as s:
            for sid in (seat_id, reports_to_seat_id):
                seat = s.get(Seat, sid)
                if seat is None or seat.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"seat_id={sid} not in tenant {tenant_id!r}; reporting edge refused"
                    )
            s.add(
                ReportingEdge(
                    tenant_id=tenant_id,
                    seat_id=seat_id,
                    reports_to_seat_id=reports_to_seat_id,
                )
            )
            s.commit()

    def manager_of(self, tenant_id: str, seat_id: int) -> Seat | None:
        with Session(self._engine) as s:
            edge = s.exec(
                select(ReportingEdge).where(
                    ReportingEdge.tenant_id == tenant_id,
                    ReportingEdge.seat_id == seat_id,
                )
            ).first()
            if edge is None:
                return None
            return s.get(Seat, edge.reports_to_seat_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_hierarchy.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/sqlite_store.py tests/test_hierarchy.py
git commit -m "feat(organization): departments + reporting edges (optional hierarchy, manager_of)"
```

---

## Task 8: Tenant isolation is the core invariant (negative tests)

**Files:**
- Test: `tests/test_isolation.py`

(No new implementation — the `_check` guard + `tenant_id` filters from Tasks 6–7 already enforce this. This task PROVES the invariant actively, the way the SQL filter-discipline demands.)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_isolation.py
import pytest

from fleetlib.organization import (
    CrossTenantError,
    Member,
    MemberKind,
    Seat,
    Tenant,
)


def _two_tenants(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_tenant(Tenant(tenant_id="globex"))


def test_members_query_never_crosses_tenants(store):
    _two_tenants(store)
    store.add_member("acme", Member(tenant_id="acme", name="alice", kind=MemberKind.agent))
    store.add_member("globex", Member(tenant_id="globex", name="zara", kind=MemberKind.agent))

    assert {m.name for m in store.members("acme")} == {"alice"}
    assert {m.name for m in store.members("globex")} == {"zara"}


def test_entity_tenant_mismatch_raises(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    # A seat carrying tenant_id="globex" added under "acme" is a breach.
    with pytest.raises(CrossTenantError):
        store.add_seat("acme", Seat(tenant_id="globex", role="intruder"))


def test_cross_tenant_assignment_raises(store):
    _two_tenants(store)
    acme_seat = store.add_seat("acme", Seat(tenant_id="acme", role="platform"))
    globex_member = store.add_member(
        "globex", Member(tenant_id="globex", name="zara", kind=MemberKind.agent)
    )
    # Assigning a globex member to an acme seat must NOT silently succeed.
    with pytest.raises(CrossTenantError):
        store.assign("acme", member_id=globex_member.id, seat_id=acme_seat.id)


def test_cross_tenant_reporting_edge_raises(store):
    _two_tenants(store)
    acme_seat = store.add_seat("acme", Seat(tenant_id="acme", role="a"))
    globex_seat = store.add_seat("globex", Seat(tenant_id="globex", role="b"))
    with pytest.raises(CrossTenantError):
        store.reports_to("acme", seat_id=acme_seat.id, reports_to_seat_id=globex_seat.id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_isolation.py -v`
Expected: PASS immediately — isolation is enforced by `_check` + `tenant_id` filters. If ANY test FAILS, the guard has a hole; fix `sqlite_store.py` before proceeding (this is the core invariant, not optional).

- [ ] **Step 3: No new implementation**

Isolation is enforced by the `_check` guard and `WHERE tenant_id = ?` filters added in Tasks 6–7. This task locks the invariant with negative regression tests.

- [ ] **Step 4: Run test to confirm green**

Run: `pytest tests/test_isolation.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add tests/test_isolation.py
git commit -m "test(organization): lock multi-tenant isolation — cross-tenant ops raise"
```

---

## Task 9: Escalation routing — query, never execution

**Files:**
- Modify: `src/fleetlib/organization/sqlite_store.py`
- Modify: `src/fleetlib/organization/__init__.py` (nothing new exported; method on store)
- Test: `tests/test_escalation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_escalation.py
from fleetlib.organization import Seat, Tenant


def _chain(store):
    # platform -> manager -> director  (junior to senior)
    store.add_tenant(Tenant(tenant_id="acme"))
    platform = store.add_seat("acme", Seat(tenant_id="acme", role="platform"))
    manager = store.add_seat("acme", Seat(tenant_id="acme", role="manager"))
    director = store.add_seat("acme", Seat(tenant_id="acme", role="director"))
    store.reports_to("acme", platform.id, manager.id)
    store.reports_to("acme", manager.id, director.id)
    return platform, manager, director


def test_escalate_returns_one_tier_up(store):
    platform, manager, _ = _chain(store)
    nxt = store.escalate("acme", platform.id)
    assert nxt.id == manager.id  # returns a Seat, runs nothing


def test_escalate_top_of_chain_returns_none(store):
    _, _, director = _chain(store)
    assert store.escalate("acme", director.id) is None


def test_explicit_route_overrides_reporting_chain(store):
    platform, manager, director = _chain(store)
    # An explicit EscalationRoute from platform jumps straight to director.
    store.set_escalation_route("acme", from_seat_id=platform.id, to_seat_id=director.id)
    assert store.escalate("acme", platform.id).id == director.id


def test_resolve_decider_walks_to_top(store):
    platform, _, director = _chain(store)
    decider = store.resolve_decider("acme", platform.id)
    assert decider.id == director.id  # top of the chain; still just a lookup


def test_escalate_is_pure_lookup_no_side_effects(store):
    platform, manager, _ = _chain(store)
    before = len(store.members("acme"))
    store.escalate("acme", platform.id)
    # No work order, no mutation — member count is unchanged and nothing was created.
    assert len(store.members("acme")) == before
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_escalation.py -v`
Expected: FAIL with `AttributeError: 'SqliteOrgStore' object has no attribute 'escalate'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/sqlite_store.py  — add import + methods

# extend the models import with EscalationRoute:
from fleetlib.organization.models import (
    Department,
    EscalationRoute,
    Member,
    Membership,
    ReportingEdge,
    Seat,
    Tenant,
)

    # --- escalation ROUTING (query only — no execution, no work-order ownership) ---

    def set_escalation_route(self, tenant_id: str, from_seat_id: int, to_seat_id: int) -> None:
        with Session(self._engine) as s:
            for sid in (from_seat_id, to_seat_id):
                seat = s.get(Seat, sid)
                if seat is None or seat.tenant_id != tenant_id:
                    raise CrossTenantError(
                        f"seat_id={sid} not in tenant {tenant_id!r}; route refused"
                    )
            s.add(
                EscalationRoute(
                    tenant_id=tenant_id, from_seat_id=from_seat_id, to_seat_id=to_seat_id
                )
            )
            s.commit()

    def escalate(self, tenant_id: str, seat_id: int) -> Seat | None:
        """Return the seat one tier up. Explicit EscalationRoute wins over the reporting
        edge. This is a LOOKUP — it does not run, mutate, or own a work order."""
        with Session(self._engine) as s:
            route = s.exec(
                select(EscalationRoute).where(
                    EscalationRoute.tenant_id == tenant_id,
                    EscalationRoute.from_seat_id == seat_id,
                )
            ).first()
            if route is not None:
                return s.get(Seat, route.to_seat_id)
        return self.manager_of(tenant_id, seat_id)

    def resolve_decider(self, tenant_id: str, seat_id: int) -> Seat | None:
        """Walk escalate() to the top of the chain and return the final decider seat.
        Still pure routing — the caller decides what to DO with the decider."""
        current_id = seat_id
        seen: set[int] = set()
        decider: Seat | None = None
        while current_id is not None and current_id not in seen:
            seen.add(current_id)
            nxt = self.escalate(tenant_id, current_id)
            if nxt is None:
                break
            decider = nxt
            current_id = nxt.id
        return decider
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_escalation.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/sqlite_store.py tests/test_escalation.py
git commit -m "feat(organization): escalate()/resolve_decider() — routing queries, no execution"
```

---

## Task 10: Ownership — "who owns this?"

**Files:**
- Modify: `src/fleetlib/organization/sqlite_store.py`
- Test: `tests/test_ownership.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ownership.py
from fleetlib.organization import Seat, Tenant


def test_owner_of_matches_seat_by_domain(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_seat("acme", Seat(tenant_id="acme", role="dba", domain="database"))
    store.add_seat("acme", Seat(tenant_id="acme", role="platform", domain="infrastructure"))

    owner = store.owner_of("acme", "database")
    assert owner is not None and owner.role == "dba"


def test_owner_of_unowned_domain_is_none(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_seat("acme", Seat(tenant_id="acme", role="platform", domain="infrastructure"))
    assert store.owner_of("acme", "billing") is None


def test_owner_of_is_tenant_scoped(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_tenant(Tenant(tenant_id="globex"))
    store.add_seat("globex", Seat(tenant_id="globex", role="dba", domain="database"))
    # acme has no database owner even though globex does.
    assert store.owner_of("acme", "database") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ownership.py -v`
Expected: FAIL with `AttributeError: 'SqliteOrgStore' object has no attribute 'owner_of'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/sqlite_store.py  — add method

    # --- ownership ("who owns this?") ------------------------------------------

    def owner_of(self, tenant_id: str, resource_domain: str) -> Seat | None:
        """The seat in this tenant whose domain owns the resource. Simplest concrete
        ownership model — a domain match, not an ACL."""
        with Session(self._engine) as s:
            return s.exec(
                select(Seat).where(
                    Seat.tenant_id == tenant_id,
                    Seat.domain == resource_domain,
                )
            ).first()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ownership.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/sqlite_store.py tests/test_ownership.py
git commit -m "feat(organization): owner_of — domain-matched ownership lookup, tenant-scoped"
```

---

## Task 11: Versioned policy references

**Files:**
- Modify: `src/fleetlib/organization/sqlite_store.py`
- Test: `tests/test_policy_refs.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_policy_refs.py
from fleetlib.organization import PolicyRef, Tenant


def test_add_and_get_current_policy_version(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_policy_ref("acme", PolicyRef(tenant_id="acme", name="retention", version=1, target="logs"))
    store.add_policy_ref("acme", PolicyRef(tenant_id="acme", name="retention", version=2, target="logs"))

    current = store.policy_ref("acme", "retention")
    assert current.version == 2  # current = highest version


def test_get_specific_policy_version(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_policy_ref("acme", PolicyRef(tenant_id="acme", name="retention", version=1, target="logs"))
    store.add_policy_ref("acme", PolicyRef(tenant_id="acme", name="retention", version=2, target="logs"))

    v1 = store.policy_ref("acme", "retention", version=1)
    assert v1.version == 1


def test_policy_refs_are_tenant_scoped(store):
    store.add_tenant(Tenant(tenant_id="acme"))
    store.add_tenant(Tenant(tenant_id="globex"))
    store.add_policy_ref("globex", PolicyRef(tenant_id="globex", name="retention", version=5, target="logs"))
    assert store.policy_ref("acme", "retention") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_policy_refs.py -v`
Expected: FAIL with `AttributeError: 'SqliteOrgStore' object has no attribute 'add_policy_ref'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/sqlite_store.py  — add import + methods

# extend the models import with PolicyRef:
from fleetlib.organization.models import (
    Department,
    EscalationRoute,
    Member,
    Membership,
    PolicyRef,
    ReportingEdge,
    Seat,
    Tenant,
)

    # --- versioned policy REFERENCES (not a policy engine) ---------------------

    def add_policy_ref(self, tenant_id: str, policy_ref: PolicyRef) -> PolicyRef:
        self._check(tenant_id, policy_ref)
        with Session(self._engine) as s:
            s.add(policy_ref)
            s.commit()
            s.refresh(policy_ref)
            return policy_ref

    def policy_ref(
        self, tenant_id: str, name: str, version: int | None = None
    ) -> PolicyRef | None:
        """version=None => the current (highest) version; otherwise that exact version."""
        with Session(self._engine) as s:
            stmt = select(PolicyRef).where(
                PolicyRef.tenant_id == tenant_id, PolicyRef.name == name
            )
            if version is not None:
                stmt = stmt.where(PolicyRef.version == version)
            else:
                stmt = stmt.order_by(PolicyRef.version.desc())
            return s.exec(stmt).first()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_policy_refs.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/sqlite_store.py tests/test_policy_refs.py
git commit -m "feat(organization): versioned policy references (current vs specific version)"
```

---

## Task 12: Neo4j adapter stub (SPI demonstration, raise on use)

**Files:**
- Create: `src/fleetlib/organization/adapters/__init__.py`
- Create: `src/fleetlib/organization/adapters/neo4j.py`
- Test: `tests/test_adapter_stub.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_adapter_stub.py
import pytest

from fleetlib.organization.adapters.neo4j import Neo4jOrgStore
from fleetlib.organization.errors import MissingExtraError


def test_neo4j_stub_raises_until_extra_lands():
    with pytest.raises(MissingExtraError, match="neo4j"):
        Neo4jOrgStore(uri="bolt://localhost:7687")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_adapter_stub.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fleetlib.organization.adapters'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/fleetlib/organization/adapters/__init__.py
"""Optional-extra OrgStore adapters. The Neo4j stub demonstrates the swap (reporting
edges are graph-shaped) and raises MissingExtraError until its extra + a real impl land.
sqlmodel -> Postgres needs only a different URL, so no extra stub is manufactured for it.
"""
```

```python
# src/fleetlib/organization/adapters/neo4j.py
"""Neo4j adapter — STUB. Reporting edges are naturally graph-shaped, so a graph store is
the honest 'swap the backend' demonstration. Raises until the neo4j extra + impl land."""

from __future__ import annotations

from fleetlib.organization.errors import MissingExtraError


class Neo4jOrgStore:
    def __init__(self, *args, **kwargs) -> None:
        raise MissingExtraError(
            "Neo4jOrgStore requires the optional 'neo4j' extra and a real implementation; "
            "install with: pip install fleetlib-organization[neo4j] (stub not yet implemented)"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_adapter_stub.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/fleetlib/organization/adapters tests/test_adapter_stub.py
git commit -m "feat(organization): Neo4j adapter stub (graph-shaped backend, raises on use)"
```

---

## Task 13: Full-suite green + public API lock

**Files:**
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_public_api.py
import fleetlib.organization as org


def test_public_surface_is_complete():
    expected = {
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
    }
    assert expected <= set(org.__all__)
    for name in expected:
        assert hasattr(org, name), name


def test_default_store_satisfies_protocol():
    assert isinstance(org.SqliteOrgStore(), org.OrgStore)


def test_end_to_end_directory_walkthrough():
    store = org.SqliteOrgStore()
    store.add_tenant(org.Tenant(tenant_id="acme", name="Acme"))

    platform = store.add_seat("acme", org.Seat(tenant_id="acme", role="platform", domain="infrastructure"))
    manager = store.add_seat("acme", org.Seat(tenant_id="acme", role="manager"))
    store.reports_to("acme", platform.id, manager.id)

    alice = store.add_member("acme", org.Member(tenant_id="acme", name="alice", kind=org.MemberKind.agent))
    store.assign("acme", member_id=alice.id, seat_id=platform.id)

    # who owns this?
    assert store.owner_of("acme", "infrastructure").role == "platform"
    # where does escalation go?
    assert store.escalate("acme", platform.id).id == manager.id
    # flat-fleet listing
    assert [m.name for m in store.members("acme")] == ["alice"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_public_api.py -v`
Expected: FAIL (file/test not yet present), then PASS once added since the API already exists from prior tasks. If `test_public_surface_is_complete` fails, finish wiring `__all__` in `__init__.py`.

- [ ] **Step 3: Finalize `__init__.py` exports**

Ensure `src/fleetlib/organization/__init__.py` re-exports the full surface:

```python
# src/fleetlib/organization/__init__.py
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
```

- [ ] **Step 4: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tests across all files green)

- [ ] **Step 5: Commit**

```bash
git add tests/test_public_api.py src/fleetlib/organization/__init__.py
git commit -m "test(organization): lock public API surface + end-to-end directory walkthrough"
```

---

## Self-Review Checklist (run after implementing)

1. **Charter coverage** — tenants, departments, roles/seats, memberships (human/service/agent), reporting edges, escalation routes, versioned policy refs all modeled (Task 3); `role()`/`reports_to()`/`escalate()` from the charter snippet realized as `Seat.role` + `reports_to()` + `escalate()` (Tasks 5/7/9); answers "who owns this?" (`owner_of`, Task 10) and "where does escalation go?" (`escalate`/`resolve_decider`, Task 9). ✔
2. **NO workflow execution inside organization** — `escalate()`/`resolve_decider()` are pure lookups that RETURN a seat; `test_escalate_is_pure_lookup_no_side_effects` proves nothing runs or mutates (Task 9). The store owns no work order. ✔
3. **StaticPool landmine handled** — `make_engine` uses `StaticPool` + `check_same_thread=False` for in-memory SQLite; `test_write_then_read_in_a_new_session_survives` proves the DB persists across sessions (Task 4). ✔
4. **Multi-tenant isolation is the core invariant, proven actively** — `_check` guard + `WHERE tenant_id = ?` on every read; cross-tenant read returns nothing AND cross-tenant assignment/edge **raises** `CrossTenantError` (Task 8). ✔
5. **Flat fleet is the baseline** — `department_id` optional, no manager required; `test_flat_fleet_create_member_with_seat` + `test_seat_without_edge_has_no_manager` (Tasks 6–7). Hierarchy is additive and first-class (Task 7). ✔
6. **Principles** — THIN (SQLModel entities double as Protocol objects, no engine reimplemented); `OrgStore` Protocol covers the FULL charter swap surface (tenants/seats/members/assign + departments/reporting/`manager_of` + escalation-route/`escalate` + ownership + policy-ref add/get) so a second backend must satisfy every charter deliverable, not just the flat-fleet subset (Task 5); ONE working default (`SqliteOrgStore`) + ONE honest stub (`Neo4jOrgStore`, Task 12); `tenant_id` first arg on every method. `_Dummy` in `test_store_protocol.py` mirrors the full surface; `resolve_decider` stays OFF the Protocol (convenience over `escalate`, YAGNI). ✔
7. **Packaging** — PEP 420 namespace (no `src/fleetlib/__init__.py`, asserted in Task 1), src layout, `py.typed`, hatchling, `neo4j`/`dev` extras. ✔
8. **Type/method consistency** — `tenant_id: str` first arg, `Seat.role`/`Seat.domain`, `MemberKind` (human/service/agent), `escalate -> Seat | None`, `owner_of -> Seat | None`, `policy_ref(version=None)`, `CrossTenantError` used identically across tasks. ✔
