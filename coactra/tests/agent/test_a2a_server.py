from __future__ import annotations

import pytest

pytest.importorskip("a2a")

from a2a.helpers import get_message_text, new_text_message

from coactra.agent.adapters.a2a_server import (
    A2A_ERROR_INTERNAL,
    A2A_ERROR_UNAUTHORIZED,
    A2AInboundRequest,
    make_a2a_executor,
    parse_a2a_envelope,
    render_task_text,
)


class _Verifier:
    def __init__(self) -> None:
        self.calls = []

    def verify(self, auth_header, *, requested_capability, allowed_subject_prefixes):
        self.calls.append(
            {
                "auth_header": auth_header,
                "requested_capability": requested_capability,
                "allowed_subject_prefixes": allowed_subject_prefixes,
            }
        )
        return {"agent_id": "caller-agent"}


class _Context:
    def __init__(self, message, task_id="task-1") -> None:
        self.call_context = type("CC", (), {"state": {"headers": {"authorization": "Bearer ok"}}})()
        self.message = message
        self.task_id = task_id
        self.context_id = "ctx-1"


class _Queue:
    def __init__(self) -> None:
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


def test_parse_a2a_envelope_preserves_free_text_and_extracts_capability() -> None:
    assert parse_a2a_envelope("hello") == (None, "hello")
    assert parse_a2a_envelope('{"capability": "deploy", "params": {"service": "api"}}') == (
        "deploy",
        {"service": "api"},
    )
    assert render_task_text("deploy", {"service": "api"}, "raw").startswith("deploy:")


@pytest.mark.asyncio
async def test_executor_requires_verifier_or_insecure_mode() -> None:
    async def handler(request: A2AInboundRequest) -> str:
        return "ok"

    with pytest.raises(ValueError, match="allow_unauthenticated"):
        make_a2a_executor(handler)


def test_executor_logs_when_unauthenticated_mode_is_enabled(caplog) -> None:
    async def handler(request: A2AInboundRequest) -> str:
        return "ok"

    with caplog.at_level("WARNING", logger="coactra.agent.adapters.a2a_server"):
        make_a2a_executor(handler, allow_unauthenticated=True)

    assert "allow_unauthenticated=True" in caplog.text


@pytest.mark.asyncio
async def test_executor_verifies_requested_capability_and_calls_handler() -> None:
    verifier = _Verifier()
    seen: list[A2AInboundRequest] = []

    async def handler(request: A2AInboundRequest) -> str:
        seen.append(request)
        return f"handled:{request.capability}:{request.claims['agent_id']}"

    executor = make_a2a_executor(handler, verifier=verifier)
    queue = _Queue()
    await executor.execute(
        _Context(new_text_message('{"capability": "deploy", "params": {"service": "api"}}')),
        queue,
    )

    assert verifier.calls == [
        {
            "auth_header": "Bearer ok",
            "requested_capability": "deploy",
            "allowed_subject_prefixes": ("",),
        }
    ]
    assert seen[0].capability == "deploy"
    assert seen[0].params == {"service": "api"}
    assert seen[0].task_text().startswith("deploy:")
    assert get_message_text(queue.events[0]) == "handled:deploy:caller-agent"


class _RejectingVerifier:
    def verify(self, auth_header, *, requested_capability, allowed_subject_prefixes):
        raise PermissionError("invalid token")


@pytest.mark.asyncio
async def test_executor_returns_unauthorized_when_verifier_rejects() -> None:
    seen: list[A2AInboundRequest] = []

    async def handler(request: A2AInboundRequest) -> str:
        seen.append(request)
        return "ok"

    executor = make_a2a_executor(handler, verifier=_RejectingVerifier())
    queue = _Queue()
    await executor.execute(_Context(new_text_message("hello")), queue)

    assert seen == []
    assert get_message_text(queue.events[0]) == f"error: {A2A_ERROR_UNAUTHORIZED}"


@pytest.mark.asyncio
async def test_executor_redacts_handler_exceptions() -> None:
    async def handler(request: A2AInboundRequest) -> str:
        raise RuntimeError("secret-internal-detail")

    executor = make_a2a_executor(handler, verifier=_Verifier())
    queue = _Queue()
    await executor.execute(_Context(new_text_message("hello")), queue)

    message = get_message_text(queue.events[0])
    assert message == f"error: {A2A_ERROR_INTERNAL}"
    assert "secret-internal-detail" not in message
    assert "Traceback" not in message
