"""Pydantic-ai stream event mapping."""
from __future__ import annotations

from typing import Any, AsyncIterator

from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    TextPart,
    ThinkingPart,
    ToolCallPart,
    ToolReturnPart,
)

from coactra.agent.events import Assistant, Event, Thinking, ToolCall, ToolResult


async def iter_call_tools_node_events(
    node: Any,
    run_ctx: Any,
    *,
    run_id: str,
    seq: int,
    tool_calls: list[ToolCall],
) -> AsyncIterator[tuple[Event, int]]:
    """Map one pydantic-ai call-tools node into Coactra stream events."""
    for part in node.model_response.parts:
        if isinstance(part, TextPart) and part.content:
            yield Assistant(run_id=run_id, seq=seq, text=part.content), seq + 1
            seq += 1
        elif isinstance(part, ThinkingPart) and part.content:
            yield Thinking(run_id=run_id, seq=seq, text=part.content), seq + 1
            seq += 1

    async with node.stream(run_ctx) as tool_stream:
        async for ev in tool_stream:
            if isinstance(ev, FunctionToolCallEvent):
                call = ev.part
                tool_call = ToolCall(
                    run_id=run_id,
                    seq=seq,
                    id=getattr(call, "tool_call_id", "") or "",
                    name=getattr(call, "tool_name", "") or "",
                    args=call.args_as_dict() if isinstance(call, ToolCallPart) else {},
                )
                tool_calls.append(tool_call)
                yield tool_call, seq + 1
                seq += 1
            elif isinstance(ev, FunctionToolResultEvent):
                part = ev.part
                is_return = isinstance(part, ToolReturnPart)
                yield ToolResult(
                    run_id=run_id,
                    seq=seq,
                    id=getattr(part, "tool_call_id", "") or "",
                    name=getattr(part, "tool_name", "") or "",
                    result=getattr(part, "content", None) if is_return else None,
                    error=None if is_return else str(getattr(part, "content", "")),
                ), seq + 1
                seq += 1
