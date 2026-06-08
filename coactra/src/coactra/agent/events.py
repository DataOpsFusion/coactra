"""Public event DTOs and RunResult for the elegant Agent SDK.

Frozen, discriminated dataclasses. Every event carries run identity (run_id, seq)
so streams can be correlated, replayed, or traced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class _Base:
    run_id: str = ""
    seq: int = 0


@dataclass(frozen=True, slots=True)
class Assistant(_Base):
    text: str = ""


@dataclass(frozen=True, slots=True)
class Thinking(_Base):
    text: str = ""


@dataclass(frozen=True, slots=True)
class ToolCall(_Base):
    id: str = ""
    name: str = ""
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolResult(_Base):
    id: str = ""
    name: str = ""
    result: Any = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class Usage(_Base):
    tokens: int = 0
    cost: float = 0.0


@dataclass(frozen=True, slots=True)
class Status(_Base):
    state: Literal["running", "finished", "error", "cancelled"] = "running"


Event = Assistant | Thinking | ToolCall | ToolResult | Usage | Status


@dataclass(frozen=True, slots=True)
class RunResult:
    status: Literal["finished", "error", "cancelled"]
    text: str = ""
    output: Any = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage | None = None
    messages: tuple[Any, ...] = ()
    error: str | None = None

    @classmethod
    def finished(
        cls,
        *,
        text: str = "",
        output: Any = None,
        usage: Usage | None = None,
        tool_calls: tuple[ToolCall, ...] = (),
        messages: tuple[Any, ...] = (),
    ) -> RunResult:
        return cls(
            status="finished",
            text=text,
            output=output,
            usage=usage,
            tool_calls=tool_calls,
            messages=messages,
        )

    @classmethod
    def failed(cls, error: str) -> RunResult:
        return cls(status="error", error=error)
