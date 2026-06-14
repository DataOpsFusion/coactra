"""Process-level safety: the library's tables must be isolatable in one process.

REGRESSION GUARD for ``sqlalchemy.exc.InvalidRequestError: Table 'tenant' is already
defined for this MetaData instance``. The directory ``table=True`` models used to
register onto the process-global ``SQLModel.metadata``, which is shared with every
other SQLModel table in the interpreter — including a HOST application's own tables
(homelab-mcp also uses SQLModel). A second registration of the same table name (a
re-import under a different identity, two stores, or a host app that also defines a
``tenant`` table) then blew up. The fix isolates the org tables in a private
``MetaData``; these tests pin that behavior.
"""

from __future__ import annotations

import sqlmodel
from sqlmodel import Field, Session, SQLModel, select

from coactra.team.directory import (
    Member,
    Organization,
    Tenant,
    make_org_store,
)

# Every directory table name owned by this library.
ORG_TABLE_NAMES = {
    "tenant",
    "department",
    "seat",
    "member",
    "membership",
    "reportingedge",
    "escalationroute",
    "policyref",
    "nodegrant",
    "memberoverride",
}


def test_two_stores_plus_domain_org_in_one_process_does_not_raise():
    # The exact real-world trigger: a host builds a SqliteOrgStore for one purpose AND
    # an Organization-based ACL for another, in the SAME process. The second table
    # registration must NOT raise InvalidRequestError.
    s1 = make_org_store("sqlite://")  # registers + creates tables
    s2 = make_org_store("sqlite://")  # second store in same process -> must NOT raise
    assert s1 is not s2

    org = Organization.root(tenant="t", name="o")
    # Exercises the SQLModel-class import path again via the domain layer.
    org.hire("a", kind="agent", permissions={"x"})


def test_org_tables_do_not_leak_into_global_sqlmodel_metadata():
    # Importing/using the library must not register its tables onto the shared
    # SQLModel.metadata, or a host app's same-named tables would collide.
    make_org_store("sqlite://")
    leaked = ORG_TABLE_NAMES & set(sqlmodel.SQLModel.metadata.tables)
    assert leaked == set(), f"org tables leaked into global SQLModel.metadata: {leaked}"


def test_host_app_can_define_its_own_tenant_table_without_collision():
    # A host application that ALSO uses SQLModel and happens to declare a 'tenant'
    # table on the global metadata must not collide with this library.
    make_org_store("sqlite://")

    class _HostTenant(SQLModel, table=True):
        __tablename__ = "tenant"
        id: int = Field(primary_key=True)

    assert _HostTenant.__tablename__ == "tenant"


def test_store_still_creates_and_queries_tables_after_isolation():
    # Guards the create_all coupling: tables live in the private metadata now, so
    # make_engine must create_all on THAT metadata — otherwise every query 500s with
    # "no such table". A real write + read proves the tables exist and work.
    store = make_org_store("sqlite://")
    store.add_tenant(Tenant(tenant_id="t1", name="one"))
    store.add_member("t1", Member(tenant_id="t1", name="alice"))
    assert [m.name for m in store.members("t1")] == ["alice"]


def test_tables_registered_on_private_metadata():
    from coactra.team.directory.models import org_metadata

    assert set(org_metadata.tables) >= ORG_TABLE_NAMES


def test_engine_create_all_targets_private_metadata():
    # The store's engine must have the org tables physically created.
    store = make_org_store("sqlite://")
    engine = store._engine
    with Session(engine) as s:
        # No "no such table" error => create_all hit the right metadata.
        assert s.exec(select(Tenant)).all() == []
        assert s.exec(select(Member)).all() == []
