"""AgentRuntimePort + the default pydantic-ai runtime (Slice 1: run only)."""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic_ai import Agent as PydAgent

from coactra.agent.sdk.events import RunResult, Usage
from coactra.agent.sdk.models import normalize_model_id


@runtime_checkable
class AgentRuntimePort(Protocol):
    async def run(self, prompt: str, *, run_id: str, output_type: type | None = None,
                  message_history: list[Any] | None = None) -> RunResult: ...


class PydanticAIRuntime:
    """Default runtime. `model` is a str (litellm-style id) or a pydantic-ai model instance
    (e.g. FunctionModel/TestModel in tests)."""

    def __init__(self, *, model: Any, instructions: str | None = None,
                 tools: list[Any] | None = None) -> None:
        self._model = normalize_model_id(model) if isinstance(model, str) else model
        self._instructions = instructions
        self._tools = tools or []

    def _build(self, output_type: type | None) -> PydAgent:
        kwargs: dict[str, Any] = {"instructions": self._instructions, "tools": self._tools}
        if output_type is not None:
            kwargs["output_type"] = output_type
        return PydAgent(self._model, **kwargs)

    def _usage(self, result: Any, run_id: str) -> Usage | None:
        # pydantic-ai 1.105: `result.usage` is a property (calling it is deprecated).
        try:
            u = result.usage
            return Usage(run_id=run_id, seq=0, tokens=getattr(u, "total_tokens", 0) or 0)
        except Exception:
            return None

    async def run(self, prompt: str, *, run_id: str, output_type: type | None = None,
                  message_history: list[Any] | None = None) -> RunResult:
        agent = self._build(output_type)
        result = await agent.run(prompt, message_history=message_history)
        output = result.output
        text = output if isinstance(output, str) else ""
        return RunResult.finished(
            text=text,
            output=None if isinstance(output, str) else output,
            usage=self._usage(result, run_id),
            messages=tuple(result.all_messages()),
        )
