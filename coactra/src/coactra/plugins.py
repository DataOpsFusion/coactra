"""Tiny public plugin hook surface for the Coactra shell."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from inspect import isawaitable
from types import MappingProxyType
from typing import Any, Mapping, Protocol

from coactra.errors import CoactraError, ErrorCode, coactra_error_from_exception
from coactra.scope import CoactraScope


@dataclass(frozen=True, slots=True)
class HookContext:
    """Immutable context passed to plugin hooks."""

    scope: CoactraScope
    session_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


class Plugin(Protocol):
    """Marker Protocol for hook objects.

    Hooks are optional methods. Supported hook names:
    - ``on_task_start(context, task)``
    - ``on_task_end(context, task, result)``
    - ``on_task_error(context, task, error)``
    """

    name: str


class PluginError(CoactraError):
    """Raised when a plugin hook fails."""

    def __init__(self, plugin_name: str, hook_name: str, cause: BaseException) -> None:
        super().__init__(
            f"plugin {plugin_name!r} failed during {hook_name}",
            code=ErrorCode.PLUGIN,
            retryable=False,
            details={"plugin": plugin_name, "hook": hook_name},
            cause=cause,
        )


class PluginManager:
    """Calls plugin hooks in registration order with explicit error wrapping."""

    def __init__(self, plugins: Iterable[Plugin] = ()) -> None:
        self._plugins = tuple(plugins)

    @property
    def plugins(self) -> tuple[Plugin, ...]:
        return self._plugins

    async def task_start(self, context: HookContext, task: Any) -> None:
        await self._call("on_task_start", context, task)

    async def task_end(self, context: HookContext, task: Any, result: Any) -> None:
        await self._call("on_task_end", context, task, result)

    async def task_error(
        self, context: HookContext, task: Any, error: CoactraError
    ) -> None:
        await self._call("on_task_error", context, task, error)

    async def _call(self, hook_name: str, *args: Any) -> None:
        for plugin in self._plugins:
            hook = getattr(plugin, hook_name, None)
            if hook is None:
                continue
            try:
                value = hook(*args)
                if isawaitable(value):
                    await value
            except BaseException as exc:
                if isinstance(exc, PluginError):
                    raise
                name = getattr(plugin, "name", plugin.__class__.__name__)
                raise PluginError(str(name), hook_name, exc) from exc


def normalize_plugin_error(exc: BaseException) -> CoactraError:
    return coactra_error_from_exception(exc, code=ErrorCode.PLUGIN)


__all__ = [
    "HookContext",
    "Plugin",
    "PluginError",
    "PluginManager",
    "normalize_plugin_error",
]
