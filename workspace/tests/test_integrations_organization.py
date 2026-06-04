from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("pytest_asyncio")
pytest.importorskip("structlog")
pytest.importorskip("coactra.organization")
pytest.importorskip("coactra.memory")

from coactra.memory import Scope
from coactra.workspace.integrations.memory import distill_journal
from coactra.workspace.integrations.organization import (
    MemoryAcl,
    ScopeViolation,
    scope_write_action,
    write_action,
)


def test_acl_allows_own_scope_and_denies_other_scope():
    acl = MemoryAcl.for_own_scope(tenant="default", agent_name="platform")
    acl.check_write("platform", Scope(tenant="default", agent="platform"))
    with pytest.raises(ScopeViolation):
        acl.check_write("platform", Scope(tenant="default", agent="security"))
    assert write_action("default", "platform") == "memory:write:default:platform"


def test_acl_can_allow_named_department_scope_without_company_scope():
    department = Scope(tenant="default", namespace="department/infrastructure")
    company = Scope(tenant="default", namespace="company")
    acl = MemoryAcl.for_scopes(
        tenant="default",
        agent_name="platform",
        writable_scopes=[department],
    )
    acl.check_write("platform", department)
    with pytest.raises(ScopeViolation):
        acl.check_write("platform", company)
    assert (
        scope_write_action(department)
        == "memory:write:default:@:department/infrastructure:*:*"
    )


def test_acl_rejects_cross_tenant_scope_configuration():
    with pytest.raises(ValueError, match="ACL tenant"):
        MemoryAcl.for_scopes(
            tenant="default",
            agent_name="platform",
            writable_scopes=[Scope(tenant="other", namespace="company")],
        )


@pytest.mark.asyncio
async def test_distiller_acl_denial_happens_before_model_or_memory_call(tmp_path: Path):
    journal = tmp_path / "journal"
    journal.mkdir()
    (journal / "2026-05-27.md").write_text("did stuff")
    llm = AsyncMock()
    memory = AsyncMock()
    acl = MemoryAcl.for_own_scope(tenant="default", agent_name="platform")

    with pytest.raises(ScopeViolation):
        await distill_journal(
            journal_dir=journal,
            agent_id="platform",
            llm=llm,
            memory=memory,
            scope=Scope(tenant="default", agent="security"),
            acl=acl,
        )

    llm.ainvoke.assert_not_awaited()
    memory.remember.assert_not_awaited()
