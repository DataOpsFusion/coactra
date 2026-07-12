"""Optional runtime integration wiring."""

from __future__ import annotations

import inspect
from typing import Any

from coactra.scope import Scope


def bind_runtime_memory(memory: Any, *, scope: Scope) -> Any:
    """Bind a memory spec to the complete runtime scope."""
    if memory is None:
        return None

    from coactra.agent.memory import bind_memory  # noqa: PLC0415

    return bind_memory(memory, scope)


def bind_runtime_workspace(workspace: Any, *, scope: Scope) -> tuple[Any, list[Any]]:
    """Open a workspace and expose its agent tools."""
    if workspace is None:
        return None, []

    from coactra.agent.workspace_tools import workspace_tools  # noqa: PLC0415
    from coactra.workspace import open_workspace  # noqa: PLC0415

    opened = open_workspace(
        scope=scope,
        base_dir=workspace,
    )
    return opened, workspace_tools(opened)


async def close_workspace(workspace: Any) -> None:
    """Close a workspace if it exposes sync or async close()."""
    if workspace is None:
        return
    close = getattr(workspace, "close", None)
    if close is None:
        return
    result = close()
    if inspect.isawaitable(result):
        await result
