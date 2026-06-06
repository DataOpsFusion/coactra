"""The elegant async Agent facade (Slice 1: model + run/stream/structured)."""
from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from coactra.agent.sdk.events import Event, RunResult
from coactra.agent.sdk.runtime import AgentRuntimePort, PydanticAIRuntime


class Run:
    """A handle to one send(). Stream events OR await the final result (not both-consuming:
    wait() runs to completion; stream() yields events and also captures the final result)."""

    def __init__(self, runtime: AgentRuntimePort, prompt: str, *, run_id: str,
                 output_type: type | None, message_history: list[Any] | None) -> None:
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
            self._prompt, run_id=self.id, output_type=self._output_type,
            message_history=self._history, on_result=_capture,
        ):
            yield ev

    async def wait(self) -> RunResult:
        if self._result is None:
            self._result = await self._runtime.run(
                self._prompt, run_id=self.id, output_type=self._output_type,
                message_history=self._history,
            )
        return self._result


class Agent:
    """Elegant async agent facade. Slice 1 wires the model + runtime only."""

    def __init__(self, runtime: AgentRuntimePort) -> None:
        self._runtime = runtime

    @classmethod
    async def create(cls, *, model: Any, instructions: str | None = None,
                     tools: list[Any] | None = None,
                     runtime: AgentRuntimePort | None = None) -> "Agent":
        rt = runtime or PydanticAIRuntime(model=model, instructions=instructions, tools=tools)
        return cls(rt)

    async def send(self, message: str, *, output: type | None = None,
                   output_type: type | None = None,
                   message_history: list[Any] | None = None) -> Run:
        resolved = output if output is not None else output_type
        return Run(self._runtime, message, run_id=f"run-{uuid.uuid4().hex[:12]}",
                   output_type=resolved, message_history=message_history)

    async def run(self, message: str, *, output: type | None = None,
                  output_type: type | None = None,
                  message_history: list[Any] | None = None) -> Any:
        resolved = output if output is not None else output_type
        result = await (await self.send(message, output_type=resolved,
                                        message_history=message_history)).wait()
        return result.output if resolved is not None else result.text

    async def aclose(self) -> None:
        # Slice 1 has no network resources to close; later slices close MCP/A2A clients here.
        return None

    async def __aenter__(self) -> "Agent":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()
