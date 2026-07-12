"""Tool invocation protocol for workflow engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from coactra.scope import Scope


@dataclass(frozen=True, slots=True)
class ToolContext:
    actor: str | None = None
    scope: Scope | None = None
    policy: Any | None = None
    run_context: Any | None = None


@runtime_checkable
class ToolInvoker(Protocol):
    async def call(
        self,
        *,
        server: str,
        tool: str,
        params: dict[str, Any],
        context: ToolContext | None = None,
    ) -> Any:
        """Invoke one external tool and return its result."""
        ...
