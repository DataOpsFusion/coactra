from __future__ import annotations

import pytest

from coactra import Scope
from coactra.workspace.integrations.directory import MemoryAcl, ScopeViolation


class FakeOrg:
    def __init__(self, permissions: set[str]) -> None:
        self.permissions = permissions

    def can(self, member, action: str) -> bool:
        return action in self.permissions


def test_memory_acl_checks_read_and_write_separately():
    scope = Scope(tenant_id="acme", agent_id="builder")
    acl = MemoryAcl(
        FakeOrg({"memory:read:acme:default:builder:*"}),
        member_for={"builder": object()},
    )

    acl.check_read("builder", scope)
    with pytest.raises(ScopeViolation):
        acl.check_write("builder", scope)
