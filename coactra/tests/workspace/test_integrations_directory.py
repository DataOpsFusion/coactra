from __future__ import annotations

from types import SimpleNamespace

import pytest

from coactra.workspace.integrations.directory import MemoryAcl, ScopeViolation


class FakeOrg:
    def __init__(self, permissions: set[str]) -> None:
        self.permissions = permissions

    def can(self, member, action: str) -> bool:
        return action in self.permissions


def test_memory_acl_checks_read_and_write_separately():
    scope = SimpleNamespace(tenant="acme", agent="builder", namespace=None, session=None)
    acl = MemoryAcl(
        FakeOrg({"memory:read:acme:builder"}),
        member_for={"builder": object()},
    )

    acl.check_read("builder", scope)
    with pytest.raises(ScopeViolation):
        acl.check_write("builder", scope)
