"""Optional runtime integration wiring."""
from __future__ import annotations

import inspect
from typing import Any


def bind_runtime_memory(memory: Any, *, tenant: str, agent: str) -> Any:
    """Bind a memory spec to the runtime scope used by Agent.create."""
    if memory is None:
        return None

    from coactra.agent.memory import bind_memory  # noqa: PLC0415
    from coactra.memory.types import Scope as MemScope  # noqa: PLC0415

    return bind_memory(memory, MemScope(tenant=tenant, agent=agent))


def bind_runtime_workspace(workspace: Any, *, tenant: str, agent: str) -> tuple[Any, list[Any]]:
    """Open a workspace and expose its agent tools."""
    if workspace is None:
        return None, []

    from coactra.agent.workspace_tools import workspace_tools  # noqa: PLC0415
    from coactra.workspace import open_workspace  # noqa: PLC0415
    from coactra.workspace.scope import Scope as WsScope  # noqa: PLC0415

    opened = open_workspace(
        scope=WsScope(tenant_id=tenant, agent_id=agent),
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
