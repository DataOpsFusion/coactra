"""Run handle returned by Agent.send()."""
from __future__ import annotations

from typing import Any, AsyncIterator

from coactra.agent.events import Event, RunResult
from coactra.agent.ports import AgentRuntimePort


class Run:
    """A handle to one send(). Stream events or await the final result."""

    def __init__(
        self,
        runtime: AgentRuntimePort,
        prompt: str,
        *,
        run_id: str,
        output_type: type | None,
        message_history: list[Any] | None,
    ) -> None:
        self._runtime = runtime
        self._prompt = prompt
        self.id = run_id
        self._output_type = output_type
        self._history = message_history
        self._result: RunResult | None = None

    async def stream(self) -> AsyncIterator[Event]:
        def _capture(result: RunResult) -> None:
            if self._result is None:
                self._result = result

        async for ev in self._runtime.stream(
            self._prompt,
            run_id=self.id,
            output_type=self._output_type,
            message_history=self._history,
            on_result=_capture,
        ):
            yield ev

    async def wait(self) -> RunResult:
        if self._result is None:
            self._result = await self._runtime.run(
                self._prompt,
                run_id=self.id,
                output_type=self._output_type,
                message_history=self._history,
            )
        return self._result
