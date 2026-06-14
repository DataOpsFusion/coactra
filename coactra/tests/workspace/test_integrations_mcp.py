from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("pytest_asyncio")

from coactra.workspace.integrations.mcp import register_recall_tool


class FakeServer:
    def __init__(self):
        self.tools = {}

    def tool(self, function):
        self.tools[function.__name__] = function
        return function


@dataclass
class Recollection:
    text: str
    source_id: str
    when: datetime | None


@pytest.mark.asyncio
async def test_register_recall_tool_binds_memory_and_scope():
    server = FakeServer()
    memory = AsyncMock()
    scope = object()
    memory.recall.return_value = [
        Recollection("fact", "source-1", datetime(2026, 6, 2, tzinfo=UTC))
    ]
    register_recall_tool(server, memory, scope)

    result = await server.tools["recall_facts"]("query", limit=4)

    memory.recall.assert_awaited_once_with("query", scope=scope, k=4)
    assert result == [{"fact": "fact", "uuid": "source-1", "valid_at": "2026-06-02 00:00:00+00:00"}]
    assert "publish_memory" not in server.tools


@pytest.mark.asyncio
async def test_shared_recall_is_limited_to_prebound_aliases():
    server = FakeServer()
    memory = AsyncMock()
    agent_scope = object()
    department_scope = object()
    company_scope = object()
    memory.recall.side_effect = [
        [Recollection("department fact", "d1", None)],
        [Recollection("company fact", "c1", None)],
    ]
    register_recall_tool(
        server,
        memory,
        agent_scope,
        scope_aliases={"department": department_scope, "company": company_scope},
    )

    result = await server.tools["recall_facts"]("query", scopes=["department", "company"], limit=4)

    assert result == [
        {
            "fact": "department fact",
            "uuid": "d1",
            "valid_at": "",
            "scope": "department",
        },
        {"fact": "company fact", "uuid": "c1", "valid_at": "", "scope": "company"},
    ]
    with pytest.raises(ValueError, match="unknown memory scopes"):
        await server.tools["recall_facts"]("query", scopes=["other-tenant"])


@pytest.mark.asyncio
async def test_publish_memory_checks_acl_before_writing():
    server = FakeServer()
    memory = AsyncMock()
    acl = SimpleNamespace(check_write=Mock())
    department_scope = object()
    register_recall_tool(
        server,
        memory,
        object(),
        scope_aliases={"department": department_scope},
        acl=acl,
        actor="platform",
    )

    result = await server.tools["publish_memory"](" reviewed fact ", scope="department")

    acl.check_write.assert_called_once_with("platform", department_scope)
    memory.remember.assert_awaited_once_with(["reviewed fact"], scope=department_scope)
    assert result == {"status": "published", "scope": "department"}
