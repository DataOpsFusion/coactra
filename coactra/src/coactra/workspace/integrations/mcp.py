"""MCP tool registration helpers for workspace-backed agent runtimes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _select_scopes(bound: Mapping[str, Any], selected: list[str] | None) -> list[tuple[str, Any]]:
    aliases = selected or ["agent"]
    unknown = sorted(set(aliases) - set(bound))
    if unknown:
        raise ValueError(f"unknown memory scopes: {', '.join(unknown)}")
    return [(alias, bound[alias]) for alias in aliases]


def register_recall_tool(
    mcp_server: object,
    memory: Any,
    scope: Any,
    *,
    scope_aliases: Mapping[str, Any] | None = None,
    acl: Any = None,
    actor: str | None = None,
) -> None:
    """Register allowlisted recall and optional publish tools backed by ``memory``.

    ``scope`` is the default agent scope. Hosts may
    bind additional aliases such as ``department`` and ``company``; callers can select
    only those pre-bound aliases, never construct an arbitrary cross-tenant scope.
    """
    bound = {"agent": scope, **dict(scope_aliases or {})}

    @mcp_server.tool
    async def recall_facts(
        query: str,
        scopes: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Recall facts from one or more allowlisted scopes."""
        rows: list[dict] = []
        seen: set[tuple[str, str]] = set()
        selected = _select_scopes(bound, scopes)
        for alias, selected_scope in selected:
            recollections = await memory.recall(query, scope=selected_scope, k=limit)
            for recollection in recollections:
                marker = (recollection.source_id, recollection.text)
                if marker in seen:
                    continue
                seen.add(marker)
                row = {
                    "fact": recollection.text,
                    "uuid": recollection.source_id,
                    "valid_at": str(recollection.when) if recollection.when is not None else "",
                }
                if len(bound) > 1:
                    row["scope"] = alias
                rows.append(row)
        return rows[:limit]

    if acl is None or actor is None:
        return

    @mcp_server.tool
    async def publish_memory(fact: str, scope: str = "agent") -> dict[str, str]:
        """Publish one reviewed fact into an allowlisted writable memory scope."""
        clean = fact.strip()
        if not clean:
            raise ValueError("fact may not be empty")
        selected = _select_scopes(bound, [scope])
        _, target = selected[0]
        acl.check_write(actor, target)
        await memory.remember([clean], scope=target)
        return {"status": "published", "scope": scope}
