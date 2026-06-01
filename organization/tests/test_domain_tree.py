"""Domain tree: the Organization composite (root + add_child) and DN-style paths.

In-memory only — no store touches these tests. The aggregate is a tree node:
a root carries the tenant, children are OUs, members are principals living on a node.
"""

import pytest

from coactra.organization import CrossTenantError, Organization
from coactra.organization.domain import MemberKind


def test_root_carries_tenant_and_name():
    acme = Organization.root(tenant="acme", name="Acme")
    assert acme.tenant == "acme"
    assert acme.name == "Acme"
    assert acme.parent is None


def test_add_child_builds_the_ou_tree():
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    rnd = eng.add_child("R&D")

    assert eng.parent is acme
    assert rnd.parent is eng
    assert [c.name for c in acme.children] == ["Engineering"]
    assert [c.name for c in eng.children] == ["R&D"]
    # children inherit the tenant from the root — no cross-tenant child possible
    assert rnd.tenant == "acme"


def test_node_path_excludes_root_name_uses_tenant_then_node_names():
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    rnd = eng.add_child("R&D")
    # DN-style: tenant id leads, then the OU node names down to this node.
    assert acme.path == "acme"
    assert eng.path == "acme/Engineering"
    assert rnd.path == "acme/Engineering/R&D"
    assert rnd.dn == "acme/Engineering/R&D"


def test_member_dn_appends_member_name_to_its_node_path():
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    rnd = eng.add_child("R&D")
    ada = rnd.hire(name="ada", kind="human", role="lead")
    assert ada.dn == "acme/Engineering/R&D/ada"


def test_manager_is_the_parent_node_none_at_root():
    acme = Organization.root(tenant="acme", name="Acme")
    eng = acme.add_child("Engineering")
    assert eng.manager is acme
    assert acme.manager is None


def test_hire_records_a_principal_with_kind():
    acme = Organization.root(tenant="acme", name="Acme")
    svc = acme.hire(name="deployer", kind="service")
    assert svc.name == "deployer"
    assert svc.kind is MemberKind.service
    assert svc.node is acme
    assert acme.members() == [svc]
