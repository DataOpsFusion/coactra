"""Dependency-light Kernel and Session shell for function-first Coactra apps."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass, field
from inspect import isawaitable
from types import MappingProxyType
from typing import Any, Protocol
from uuid import uuid4

from coactra.errors import CoactraError, ErrorCode, coactra_error_from_exception
from coactra.plugins import HookContext, Plugin, PluginManager
from coactra.scope import CoactraScope


@dataclass(frozen=True, slots=True)
class Task:
    """Small task DTO for the umbrella shell.

    ``Task`` is intentionally generic. Durable business work still belongs in
    ``coactra.jobs.WorkOrder``; reusable procedures still belong in
    ``coactra.jobs.workflow.Procedure``.
    """

    name: str
    input: Mapping[str, Any] = field(default_factory=dict)
    timeout_s: float | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Task.name must be a non-empty string")
        object.__setattr__(self, "input", MappingProxyType(dict(self.input)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Result DTO returned by ``Session.run``."""

    status: str
    output: Any = None
    artifacts: tuple[str, ...] = ()
    error: CoactraError | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    @classmethod
    def completed(
        cls,
        output: Any = None,
        *,
        artifacts: Iterable[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> "TaskResult":
        return cls(
            status="completed",
            output=output,
            artifacts=tuple(artifacts),
            metadata=metadata or {},
        )

    @classmethod
    def failed(
        cls,
        error: CoactraError,
        *,
        metadata: Mapping[str, Any] | None = None,
    ) -> "TaskResult":
        return cls(status="failed", error=error, metadata=metadata or {})


class TaskHandler(Protocol):
    """Callable task handler used by ``Kernel``."""

    def __call__(
        self, context: HookContext, task: Task
    ) -> TaskResult | Any | Awaitable[TaskResult | Any]:
        ...


class Kernel:
    """Configured root object for beta Coactra shell examples."""

    def __init__(
        self,
        *,
        handlers: Mapping[str, TaskHandler] | None = None,
        default_handler: TaskHandler | None = None,
        plugins: Iterable[Plugin] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        self._handlers = dict(handlers or {})
        self._default_handler = default_handler
        self._plugins = PluginManager(plugins)
        self._metadata = MappingProxyType(dict(metadata or {}))

    @classmethod
    def builder(cls) -> "KernelBuilder":
        return KernelBuilder()

    @property
    def metadata(self) -> Mapping[str, Any]:
        return self._metadata

    @property
    def plugins(self) -> tuple[Plugin, ...]:
        return self._plugins.plugins

    def session(
        self,
        scope: CoactraScope,
        *,
        session_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "Session":
        return Session(
            kernel=self,
            context=HookContext(
                scope=scope,
                session_id=session_id or str(uuid4()),
                metadata={**self._metadata, **dict(metadata or {})},
            ),
        )

    async def _run(self, context: HookContext, task: Task) -> TaskResult:
        handler = self._handlers.get(task.name, self._default_handler)
        if handler is None:
            return TaskResult.failed(
                CoactraError(
                    f"no handler registered for task {task.name!r}",
                    code=ErrorCode.VALIDATION,
                    details={"task": task.name},
                )
            )
        await self._plugins.task_start(context, task)
        try:
            value = handler(context, task)
            if isawaitable(value):
                value = await value
            result = value if isinstance(value, TaskResult) else TaskResult.completed(value)
        except BaseException as exc:
            error = coactra_error_from_exception(exc, code=ErrorCode.RUNTIME)
            result = TaskResult.failed(error)
            await self._plugins.task_error(context, task, error)
            return result
        await self._plugins.task_end(context, task, result)
        return result


class Session:
    """Per-run context created from a ``Kernel`` and immutable ``CoactraScope``."""

    def __init__(self, *, kernel: Kernel, context: HookContext) -> None:
        self._kernel = kernel
        self.context = context

    @property
    def scope(self) -> CoactraScope:
        return self.context.scope

    @property
    def session_id(self) -> str:
        return self.context.session_id

    async def run(self, task: Task) -> TaskResult:
        return await self._kernel._run(self.context, task)

    async def stream(self, task: Task):
        yield await self.run(task)


class KernelBuilder:
    """Small builder used to keep shell construction explicit."""

    def __init__(self) -> None:
        self._handlers: dict[str, TaskHandler] = {}
        self._default_handler: TaskHandler | None = None
        self._plugins: list[Plugin] = []
        self._metadata: dict[str, Any] = {}

    def with_handler(self, name: str, handler: TaskHandler) -> "KernelBuilder":
        if not isinstance(name, str) or not name:
            raise ValueError("handler name must be a non-empty string")
        self._handlers[name] = handler
        return self

    def with_default_handler(self, handler: TaskHandler) -> "KernelBuilder":
        self._default_handler = handler
        return self

    def with_plugin(self, plugin: Plugin) -> "KernelBuilder":
        self._plugins.append(plugin)
        return self

    def with_plugins(self, *plugins: Plugin) -> "KernelBuilder":
        self._plugins.extend(plugins)
        return self

    def with_metadata(self, **metadata: Any) -> "KernelBuilder":
        self._metadata.update(metadata)
        return self

    def build(self) -> Kernel:
        return Kernel(
            handlers=self._handlers,
            default_handler=self._default_handler,
            plugins=self._plugins,
            metadata=self._metadata,
        )


__all__ = [
    "Kernel",
    "KernelBuilder",
    "Session",
    "Task",
    "TaskHandler",
    "TaskResult",
]
