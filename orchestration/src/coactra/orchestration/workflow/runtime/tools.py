"""Tool invocation protocol for workflow engines."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ToolInvoker(Protocol):
    async def call(self, *, server: str, tool: str, params: dict[str, Any]) -> Any:
        """Invoke one external tool and return its result."""
        ...
