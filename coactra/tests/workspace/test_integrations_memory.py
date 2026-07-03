from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("pytest_asyncio")
pytest.importorskip("structlog")
pytest.importorskip("coactra.memory")

from coactra.memory import Scope
from coactra.workspace.integrations.memory import distill_journal


@pytest.mark.asyncio
async def test_distill_extracts_facts_and_writes_to_memory(tmp_path: Path):
    journal = tmp_path / "journal"
    journal.mkdir()
    (journal / "2026-05-27.md").write_text("Created VM 1024")
    llm = AsyncMock()
    llm.ainvoke.return_value = type("R", (), {"content": '["VM 1024 created"]'})()
    memory = AsyncMock()
    scope = Scope(tenant="default", agent="platform")

    count = await distill_journal(
        journal_dir=journal,
        agent_id="platform",
        llm=llm,
        memory=memory,
        scope=scope,
    )

    assert count == 1
    memory.remember.assert_awaited_once_with(["VM 1024 created"], scope=scope)


@pytest.mark.asyncio
async def test_distill_skips_already_distilled(tmp_path: Path):
    journal = tmp_path / "journal"
    journal.mkdir()
    (journal / "2026-05-27.md").write_text("did stuff")
    (journal / ".distilled").write_text("2026-05-27.md\n")
    llm = AsyncMock()

    count = await distill_journal(
        journal_dir=journal,
        agent_id="platform",
        llm=llm,
        memory=AsyncMock(),
        scope=Scope(tenant="default", agent="platform"),
    )

    assert count == 0
    llm.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_distill_rejects_journal_entry_symlink_escape(tmp_path: Path):
    journal = tmp_path / "journal"
    journal.mkdir()
    secret = tmp_path / "secret.md"
    secret.write_text("host secret")
    (journal / "2026-05-27.md").symlink_to(secret)
    llm = AsyncMock()

    with pytest.raises(ValueError, match="escapes journal_dir"):
        await distill_journal(
            journal_dir=journal,
            agent_id="platform",
            llm=llm,
            memory=AsyncMock(),
            scope=Scope(tenant="default", agent="platform"),
        )

    llm.ainvoke.assert_not_awaited()
