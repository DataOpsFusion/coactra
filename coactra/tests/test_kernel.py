from __future__ import annotations

import asyncio

import pytest

from coactra.errors import CoactraError, ErrorCode
from coactra.kernel import Kernel, Task, TaskResult
from coactra.plugins import HookContext, PluginError
from coactra.scope import CoactraScope


class RecordingPlugin:
    name = "recorder"

    def __init__(self) -> None:
        self.events: list[tuple[str, str, str]] = []

    def on_task_start(self, context: HookContext, task: Task) -> None:
        self.events.append(("start", context.session_id, task.name))

    async def on_task_end(
        self, context: HookContext, task: Task, result: TaskResult
    ) -> None:
        self.events.append(("end", context.session_id, result.status))

    def on_task_error(
        self, context: HookContext, task: Task, error: CoactraError
    ) -> None:
        self.events.append(("error", context.session_id, error.code.value))


def scope() -> CoactraScope:
    return CoactraScope(
        tenant_id="tenant-a",
        namespace="support",
        agent_id="triage",
        session_id="outer-session",
    )


def test_kernel_runs_registered_task_handler_with_plugins() -> None:
    plugin = RecordingPlugin()

    def triage(context: HookContext, task: Task) -> dict[str, object]:
        return {
            "tenant": context.scope.tenant_id,
            "incident": task.input["incident"],
        }

    kernel = (
        Kernel.builder()
        .with_handler("triage", triage)
        .with_plugin(plugin)
        .with_metadata(env="test")
        .build()
    )

    session = kernel.session(scope(), session_id="session-1", metadata={"run": "a"})
    result = asyncio.run(session.run(Task("triage", {"incident": "db-latency"})))

    assert result.status == "completed"
    assert result.output == {"tenant": "tenant-a", "incident": "db-latency"}
    assert session.context.metadata == {"env": "test", "run": "a"}
    assert plugin.events == [
        ("start", "session-1", "triage"),
        ("end", "session-1", "completed"),
    ]


def test_kernel_accepts_async_handler_and_task_result_passthrough() -> None:
    async def handler(context: HookContext, task: Task) -> TaskResult:
        return TaskResult.completed(
            {"scope": context.scope.key},
            artifacts=("artifact://one",),
        )

    result = asyncio.run(
        Kernel.builder()
        .with_handler("build", handler)
        .build()
        .session(scope(), session_id="session-2")
        .run(Task("build"))
    )

    assert result.status == "completed"
    assert result.output == {"scope": "tenant-a:support:triage:outer-session"}
    assert result.artifacts == ("artifact://one",)


def test_missing_handler_returns_validation_failure() -> None:
    result = asyncio.run(Kernel.builder().build().session(scope()).run(Task("missing")))

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code is ErrorCode.VALIDATION
    assert result.error.details == {"task": "missing"}


def test_handler_exception_is_normalized_and_error_hook_runs() -> None:
    plugin = RecordingPlugin()

    def explode(context: HookContext, task: Task) -> None:
        raise RuntimeError("boom")

    session = (
        Kernel.builder()
        .with_handler("explode", explode)
        .with_plugin(plugin)
        .build()
        .session(scope(), session_id="session-3")
    )

    result = asyncio.run(session.run(Task("explode")))

    assert result.status == "failed"
    assert result.error is not None
    assert result.error.code is ErrorCode.RUNTIME
    assert result.error.as_dict()["message"] == "boom"
    assert plugin.events == [
        ("start", "session-3", "explode"),
        ("error", "session-3", "runtime"),
    ]


def test_plugin_failure_is_named_and_not_swallowed() -> None:
    class BadPlugin:
        name = "bad"

        def on_task_start(self, context: HookContext, task: Task) -> None:
            raise ValueError("bad hook")

    kernel = (
        Kernel.builder()
        .with_handler("noop", lambda context, task: {"ok": True})
        .with_plugin(BadPlugin())
        .build()
    )

    with pytest.raises(PluginError) as exc_info:
        asyncio.run(kernel.session(scope()).run(Task("noop")))

    assert exc_info.value.code is ErrorCode.PLUGIN
    assert exc_info.value.details == {"plugin": "bad", "hook": "on_task_start"}


def test_session_stream_yields_single_result() -> None:
    kernel = Kernel.builder().with_handler("x", lambda context, task: "ok").build()

    async def collect() -> list[TaskResult]:
        stream = kernel.session(scope()).stream(Task("x"))
        return [result async for result in stream]

    results = asyncio.run(collect())

    assert results == [TaskResult.completed("ok")]
