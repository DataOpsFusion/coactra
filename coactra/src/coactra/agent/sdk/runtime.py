"""AgentRuntimePort + the default pydantic-ai runtime (Slice 1: run + stream)."""
from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Protocol, runtime_checkable

from pydantic_ai import Agent as PydAgent

from coactra.agent.sdk.events import (
    Assistant,
    Event,
    RunResult,
    Status,
    Thinking,
    ToolCall,
    ToolResult,
    Usage,
)


@runtime_checkable
class AgentRuntimePort(Protocol):
    async def run(self, prompt: str, *, run_id: str, output_type: type | None = None,
                  message_history: list[Any] | None = None) -> RunResult: ...

    def stream(self, prompt: str, *, run_id: str, output_type: type | None = None,
               message_history: list[Any] | None = None,
               on_result: Callable[[RunResult], None] | None = None) -> AsyncIterator[Event]: ...


class PydanticAIRuntime:
    """Default runtime. `model` is a str (litellm-style id) or a pydantic-ai model instance
    (e.g. FunctionModel/TestModel in tests)."""

    def __init__(self, *, model: Any, instructions: str | None = None,
                 tools: list[Any] | None = None,
                 api_base: str | None = None,
                 api_key: str | None = None,
                 **defaults: Any) -> None:
        if isinstance(model, str):
            # Route string ids through litellm + coactra.ai's thinking-model handling.
            # Lazy import so model-instance usage stays free of the litellm dependency.
            from coactra.agent.sdk.litellm_model import LiteLLMModel
            self._model: Any = LiteLLMModel(model, api_base=api_base, api_key=api_key, **defaults)
        else:
            # Model instance passed directly — provider config does not apply.
            self._model = model
        self._instructions = instructions
        self._tools = tools or []

    def _build(self, output_type: type | None) -> PydAgent:
        kwargs: dict[str, Any] = {"instructions": self._instructions, "tools": self._tools}
        if output_type is not None:
            kwargs["output_type"] = output_type
        return PydAgent(self._model, **kwargs)

    def _usage(self, result: Any, run_id: str, *, seq: int = 0) -> Usage | None:
        # pydantic-ai 1.105: `result.usage` is a property (the callable form is deprecated).
        # RunUsage has no `total_tokens` field, so fall back to input + output.
        try:
            u = result.usage
            tokens = getattr(u, "total_tokens", 0) or (
                (getattr(u, "input_tokens", 0) or 0) + (getattr(u, "output_tokens", 0) or 0)
            )
            return Usage(run_id=run_id, seq=seq, tokens=tokens)
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

    async def stream(self, prompt: str, *, run_id: str, output_type: type | None = None,
                     message_history: list[Any] | None = None,
                     on_result: Callable[[RunResult], None] | None = None) -> AsyncIterator[Event]:
        """Drive the pydantic-ai agent graph and yield coactra event DTOs.

        Maps pydantic-ai 1.105 graph nodes/events to the coactra event contract:
        - a completed model text part      → ``Assistant``
        - a completed model thinking part  → ``Thinking``
        - a function tool-call request     → ``ToolCall``  (from CallToolsNode.stream)
        - a function tool return           → ``ToolResult``(from CallToolsNode.stream)
        - the run's token usage             → ``Usage``
        and a single terminal ``Status`` ("finished" on success, "error" on failure).

        Tool call/result events come only from ``CallToolsNode.stream`` so they are not
        double-emitted alongside the response parts. Model parts are read from the
        already-resolved ``model_response`` (not streamed) so this works with offline
        ``FunctionModel``s that have no ``stream_function``.

        ``on_result`` (when given) receives the full ``RunResult`` derived from the same
        iteration — output, usage, tool calls, and message history — so a caller that
        streams and then awaits the result gets the rich result, not a text-only digest.
        """
        from pydantic_ai.messages import (
            FunctionToolCallEvent,
            FunctionToolResultEvent,
            TextPart,
            ThinkingPart,
            ToolCallPart,
            ToolReturnPart,
        )

        agent = self._build(output_type)
        seq = 0
        tool_calls: list[ToolCall] = []
        try:
            async with agent.iter(
                prompt, output_type=output_type, message_history=message_history,
            ) as run:
                async for node in run:
                    if PydAgent.is_call_tools_node(node):
                        # Completed model response parts (text / thinking). Tool-call
                        # parts here are intentionally skipped — they surface via the
                        # tool-execution stream below as ToolCall/ToolResult pairs.
                        for part in node.model_response.parts:
                            if isinstance(part, TextPart):
                                if part.content:
                                    yield Assistant(run_id=run_id, seq=seq, text=part.content)
                                    seq += 1
                            elif isinstance(part, ThinkingPart):
                                if part.content:
                                    yield Thinking(run_id=run_id, seq=seq, text=part.content)
                                    seq += 1
                        # Stream tool execution: call request, then tool return.
                        async with node.stream(run.ctx) as tool_stream:
                            async for ev in tool_stream:
                                if isinstance(ev, FunctionToolCallEvent):
                                    call = ev.part
                                    tc = ToolCall(
                                        run_id=run_id, seq=seq,
                                        id=getattr(call, "tool_call_id", "") or "",
                                        name=getattr(call, "tool_name", "") or "",
                                        args=call.args_as_dict() if isinstance(call, ToolCallPart) else {},
                                    )
                                    tool_calls.append(tc)
                                    yield tc
                                    seq += 1
                                elif isinstance(ev, FunctionToolResultEvent):
                                    part = ev.part
                                    is_return = isinstance(part, ToolReturnPart)
                                    yield ToolResult(
                                        run_id=run_id, seq=seq,
                                        id=getattr(part, "tool_call_id", "") or "",
                                        name=getattr(part, "tool_name", "") or "",
                                        result=getattr(part, "content", None) if is_return else None,
                                        error=None if is_return else str(getattr(part, "content", "")),
                                    )
                                    seq += 1
                # All nodes consumed: the rich result is now available.
                result = run.result
                usage = self._usage(result, run_id, seq=seq) if result is not None else None
                if usage is not None:
                    yield usage
                    seq += 1
                if on_result is not None and result is not None:
                    output = result.output
                    text = output if isinstance(output, str) else ""
                    on_result(RunResult.finished(
                        text=text,
                        output=None if isinstance(output, str) else output,
                        usage=usage,
                        tool_calls=tuple(tool_calls),
                        messages=tuple(result.all_messages()),
                    ))
        except Exception:  # noqa: BLE001 - terminal error event is the contract
            yield Status(run_id=run_id, seq=seq, state="error")
            if on_result is not None:
                on_result(RunResult.failed("stream error"))
            return
        yield Status(run_id=run_id, seq=seq, state="finished")
