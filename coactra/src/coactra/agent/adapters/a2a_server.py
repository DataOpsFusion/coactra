"""Generic inbound A2A server helpers.

Hosts should provide only the runtime handler: what to do with an authorized
message. This module owns the official SDK request shapes, envelope parsing,
capability-aware verification call, task event emission, and Starlette route
assembly.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

_log = logging.getLogger(__name__)

A2A_ERROR_UNAUTHORIZED = "unauthorized"
A2A_ERROR_INTERNAL = "internal"
A2A_ERROR_INSECURE_MODE_REQUIRED = "insecure_mode_required"

A2AHandler = Callable[["A2AInboundRequest"], Awaitable[str]]


def coerce_agent_card(agent_card: Any) -> Any:
    """Return an official a2a-sdk AgentCard for HTTP serving routes.

    Coactra's public ``Agent.card`` is a curated dict used by Team/Workflow
    discovery.  Recent a2a-sdk server routes expect protobuf messages, so the
    adapter coerces the dict at the SDK boundary without changing the public
    card shape.
    """
    if hasattr(agent_card, "DESCRIPTOR"):
        return agent_card
    if not isinstance(agent_card, Mapping):
        return agent_card

    sdk = _require_a2a_server_sdk()
    types = sdk["types"]

    card = types.AgentCard(
        name=str(agent_card.get("name") or "agent"),
        description=str(agent_card.get("description") or ""),
        version=str(agent_card.get("version") or "0.0.0"),
        capabilities=types.AgentCapabilities(streaming=False),
    )
    card.default_input_modes.append("text/plain")
    card.default_output_modes.append("text/plain")

    if tenant := agent_card.get("tenant"):
        card.supported_interfaces.append(
            types.AgentInterface(
                url=str(agent_card.get("url") or ""),
                protocol_binding="JSONRPC",
                tenant=str(tenant)
            )
        )
    elif agent_card.get("url"):
        card.supported_interfaces.append(
            types.AgentInterface(
                url=str(agent_card["url"]),
                protocol_binding="JSONRPC"
            )
        )

    for skill in agent_card.get("skills", []) or []:
        if not isinstance(skill, Mapping):
            continue
        skill_id = str(skill.get("id") or "skill")
        entry = types.AgentSkill(
            id=skill_id,
            name=str(skill.get("name") or skill_id),
            description=str(skill.get("description") or ""),
        )
        entry.tags.extend(str(tag) for tag in skill.get("tags", []) or [])
        entry.input_modes.append("text/plain")
        entry.output_modes.append("text/plain")
        card.skills.append(entry)

    for name, scheme in (agent_card.get("securitySchemes") or {}).items():
        if not isinstance(scheme, Mapping):
            continue
        if scheme.get("type") == "http" and scheme.get("scheme") == "bearer":
            card.security_schemes[str(name)].http_auth_security_scheme.CopyFrom(
                types.HTTPAuthSecurityScheme(
                    scheme="bearer",
                    bearer_format=str(scheme.get("bearerFormat") or ""),
                )
            )

    return card


class A2ARequestVerifier(Protocol):
    def verify(
        self,
        auth_header: str,
        *,
        requested_capability: str,
        allowed_subject_prefixes: Sequence[str] = ("",),
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class A2AInboundRequest:
    """Authorized inbound A2A request in host-neutral form."""

    text: str
    capability: str | None
    params: Any
    task_id: str
    context_id: str
    headers: Mapping[str, str] = field(default_factory=dict)
    claims: Mapping[str, Any] = field(default_factory=dict)

    @property
    def requested_capability(self) -> str | None:
        return self.capability

    def task_text(self) -> str:
        return render_task_text(self.capability, self.params, self.text)


def parse_a2a_envelope(text: str) -> tuple[str | None, Any]:
    """Parse the small Coactra delegation envelope, preserving free text."""
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None, text
    if isinstance(obj, dict) and "capability" in obj:
        return obj.get("capability"), obj.get("params") or {}
    return None, text


def render_task_text(capability: str | None, payload: Any, raw: str) -> str:
    """Render a delegated capability + params into a plain task string."""
    if capability is None:
        return raw
    if isinstance(payload, str):
        return f"{capability}: {payload}"
    return f"{capability}: {json.dumps(payload)}"


def headers_from_context(context: Any) -> dict[str, str]:
    call_context = getattr(context, "call_context", None)
    state = getattr(call_context, "state", None) if call_context is not None else None
    if isinstance(state, dict):
        return dict(state.get("headers", {}) or {})
    return {}


def _a2a_error_message(code: str) -> str:
    return f"error: {code}"


def _require_a2a_server_sdk() -> dict[str, Any]:
    try:
        from a2a.helpers import get_message_text, new_text_message
        from a2a.server.agent_execution import AgentExecutor
        from a2a.server.request_handlers import DefaultRequestHandler
        from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
        from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
        from a2a import types
        from a2a.types import TaskState
        from a2a.utils.constants import DEFAULT_RPC_URL
        from starlette.applications import Starlette
    except ImportError as exc:  # pragma: no cover - optional extra guard
        raise RuntimeError("coactra[agent,a2a] is required for inbound A2A server") from exc
    return {
        "get_message_text": get_message_text,
        "new_text_message": new_text_message,
        "AgentExecutor": AgentExecutor,
        "DefaultRequestHandler": DefaultRequestHandler,
        "create_agent_card_routes": create_agent_card_routes,
        "create_jsonrpc_routes": create_jsonrpc_routes,
        "InMemoryTaskStore": InMemoryTaskStore,
        "TaskUpdater": TaskUpdater,
        "TaskState": TaskState,
        "types": types,
        "DEFAULT_RPC_URL": DEFAULT_RPC_URL,
        "Starlette": Starlette,
    }


def make_a2a_executor(
    handler: A2AHandler,
    *,
    verifier: A2ARequestVerifier | None = None,
    allow_unauthenticated: bool = False,
    default_capability: str = "execute",
    allowed_subject_prefixes: Sequence[str] = ("",),
) -> Any:
    """Build an official-SDK AgentExecutor around a host runtime handler."""
    if verifier is None and not allow_unauthenticated:
        raise ValueError(
            "A2A inbound task execution requires a request verifier or "
            "explicit allow_unauthenticated=True (insecure mode)"
        )
    if verifier is None and allow_unauthenticated:
        _log.warning(
            "A2A inbound task execution is running with allow_unauthenticated=True; "
            "do not use this mode outside local development"
        )

    sdk = _require_a2a_server_sdk()
    base = sdk["AgentExecutor"]
    get_message_text = sdk["get_message_text"]
    new_text_message = sdk["new_text_message"]
    task_updater_cls = sdk["TaskUpdater"]
    task_state = sdk["TaskState"]

    class CoactraA2AExecutor(base):
        async def execute(self, context: Any, event_queue: Any) -> None:
            headers = headers_from_context(context)
            text = get_message_text(context.message) if getattr(context, "message", None) else ""
            capability, payload = parse_a2a_envelope(text)
            requested = capability or default_capability
            claims: Mapping[str, Any] = {}
            if verifier is not None:
                try:
                    claims = verifier.verify(
                        headers.get("authorization", ""),
                        requested_capability=requested,
                        allowed_subject_prefixes=allowed_subject_prefixes,
                    )
                except Exception as exc:  # noqa: BLE001 - verifier type is host supplied.
                    _log.warning("A2A verifier rejected request", exc_info=exc)
                    await event_queue.enqueue_event(
                        new_text_message(_a2a_error_message(A2A_ERROR_UNAUTHORIZED))
                    )
                    return
            elif not allow_unauthenticated:
                await event_queue.enqueue_event(
                    new_text_message(_a2a_error_message(A2A_ERROR_INSECURE_MODE_REQUIRED))
                )
                return
            request = A2AInboundRequest(
                text=text,
                capability=capability,
                params=payload,
                task_id=getattr(context, "task_id", None) or "default",
                context_id=(
                    getattr(context, "context_id", None)
                    or getattr(context, "task_id", None)
                    or "default"
                ),
                headers=headers,
                claims=claims,
            )
            try:
                answer = await handler(request)
            except Exception:  # noqa: BLE001 - surface runtime failure to caller.
                _log.exception("A2A handler failed for task %s", request.task_id)
                await event_queue.enqueue_event(
                    new_text_message(_a2a_error_message(A2A_ERROR_INTERNAL))
                )
                return
            await event_queue.enqueue_event(new_text_message(answer))

        async def cancel(self, context: Any, event_queue: Any) -> None:
            updater = task_updater_cls(
                event_queue,
                getattr(context, "task_id", None) or "default",
                getattr(context, "context_id", None)
                or getattr(context, "task_id", None)
                or "default",
            )
            await updater.update_status(
                task_state.TASK_STATE_CANCELED,
                message=new_text_message("cancelled"),
            )

    return CoactraA2AExecutor()


def build_a2a_app(
    *,
    agent_card: Any,
    handler: A2AHandler,
    verifier: A2ARequestVerifier | None = None,
    allow_unauthenticated: bool = False,
    extra_routes: Sequence[Any] = (),
    task_store: Any | None = None,
    default_capability: str = "execute",
    allowed_subject_prefixes: Sequence[str] = ("",),
) -> Any:
    """Assemble a Starlette A2A app around a host runtime handler."""
    sdk = _require_a2a_server_sdk()
    official_card = coerce_agent_card(agent_card)
    request_handler = sdk["DefaultRequestHandler"](
        agent_executor=make_a2a_executor(
            handler,
            verifier=verifier,
            allow_unauthenticated=allow_unauthenticated,
            default_capability=default_capability,
            allowed_subject_prefixes=allowed_subject_prefixes,
        ),
        task_store=task_store or sdk["InMemoryTaskStore"](),
        agent_card=official_card,
    )
    routes = list(sdk["create_agent_card_routes"](official_card))
    routes += list(sdk["create_jsonrpc_routes"](request_handler, sdk["DEFAULT_RPC_URL"]))
    routes += list(extra_routes)
    return sdk["Starlette"](routes=routes)
