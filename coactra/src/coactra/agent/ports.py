"""Public runtime protocols for agent execution."""
from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Protocol, runtime_checkable

from coactra.agent.events import Event, RunResult


@runtime_checkable
class AgentRuntimePort(Protocol):
    async def run(
        self,
        prompt: str,
        *,
        run_id: str,
        output_type: type | None = None,
        message_history: list[Any] | None = None,
    ) -> RunResult: ...

    def stream(
        self,
        prompt: str,
        *,
        run_id: str,
        output_type: type | None = None,
        message_history: list[Any] | None = None,
        on_result: Callable[[RunResult], None] | None = None,
    ) -> AsyncIterator[Event]: ...
