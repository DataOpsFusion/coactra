"""Official A2A SDK adapter for policy-gated collaboration.

The agent core owns collaboration policy. This adapter owns only the wire:
token lookup, official SDK client construction, send_message, and reply-text
collection. Hosts provide endpoint/audience resolution because those are
deployment concerns.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from typing import Any

from coactra.agent.domain import AgentRef, Scope

TokenProvider = Callable[[str, list[dict[str, Any]] | None], Awaitable[str]]
EndpointResolver = Callable[[AgentRef], str]
AudienceResolver = Callable[[AgentRef], str]
MessageBuilder = Callable[[str], str | Mapping[str, Any]]


def _require_a2a_sdk() -> dict[str, Any]:
    try:
        import httpx
        from a2a.client import ClientConfig, create_client
        from a2a.helpers import get_message_text, new_text_message
        from a2a.types import SendMessageRequest
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "coactra[a2a] is required for OfficialA2AClient"
        ) from exc
    return {
        "httpx": httpx,
        "ClientConfig": ClientConfig,
        "create_client": create_client,
        "get_message_text": get_message_text,
        "new_text_message": new_text_message,
        "SendMessageRequest": SendMessageRequest,
    }


def _part_text(part: Any) -> str:
    # Pydantic Part wraps the variant in `.root`; proto Part exposes `.text` directly.
    root = getattr(part, "root", part)
    return getattr(root, "text", "") or ""


def _parts_text(obj: Any) -> str:
    return "".join(_part_text(part) for part in (getattr(obj, "parts", None) or []))


def _text_from(obj: Any) -> str:
    """Extract text from common a2a-sdk response shapes.

    The SDK can yield a Message, Task, StreamResponse-like wrapper, or a
    ``(Task, UpdateEvent)`` tuple. Text may live directly on message parts,
    ``task.status.message``, artifacts, or history.
    """
    if obj is None:
        return ""

    inner = getattr(obj, "message", None)
    if inner is not None and inner is not obj:
        text = _text_from(inner)
        if text:
            return text

    task = getattr(obj, "task", None)
    if task is not None and task is not obj:
        text = _text_from(task)
        if text:
            return text

    try:
        text = _require_a2a_sdk()["get_message_text"](obj)
        if text:
            return text
    except Exception:  # noqa: BLE001 - not every SDK shape is a pydantic Message.
        pass

    text = _parts_text(obj)
    if text:
        return text

    out: list[str] = []
    status = getattr(obj, "status", None)
    status_message = getattr(status, "message", None) if status is not None else None
    if status_message is not None:
        out.append(_text_from(status_message))
    for artifact in getattr(obj, "artifacts", None) or []:
        out.append(_parts_text(artifact))
    if not any(out):
        for message in getattr(obj, "history", None) or []:
            out.append(_text_from(message))
    return "\n".join(text for text in out if text)


async def collect_text(responses: AsyncIterator[Any]) -> str:
    """Collect SDK send_message responses into a single de-duplicated string."""
    seen: list[str] = []
    async for item in responses:
        candidates = list(item) if isinstance(item, tuple) else [item]
        for candidate in candidates:
            text = _text_from(candidate)
            if text and text not in seen:
                seen.append(text)
    return "\n".join(seen)


def _message_text(message: str | Mapping[str, Any]) -> str:
    if isinstance(message, str):
        return message
    return json.dumps(message)


class OfficialA2AClient:
    """Small official-SDK outbound caller.

    It deliberately does not know how to find agents. Callers pass endpoint and
    audience explicitly so hosts can use env vars, registries, service discovery,
    or static config without changing the adapter.
    """

    def __init__(
        self,
        token_provider: TokenProvider | None = None,
        *,
        timeout: float = 60.0,
    ) -> None:
        self._token_provider = token_provider
        self._timeout = timeout

    async def call(
        self,
        *,
        agent_id: str,  # noqa: ARG002 - useful to test/fake clients and logs.
        endpoint: str,
        audience: str,
        message: str | Mapping[str, Any],
        delegation_chain: list[dict[str, Any]] | None = None,
    ) -> str:
        sdk = _require_a2a_sdk()
        headers: dict[str, str] = {}
        if self._token_provider is not None:
            token = await self._token_provider(audience, delegation_chain)
            headers["Authorization"] = f"Bearer {token}"

        httpx = sdk["httpx"]
        http_client = httpx.AsyncClient(headers=headers, timeout=self._timeout)
        client = await sdk["create_client"](
            endpoint,
            client_config=sdk["ClientConfig"](httpx_client=http_client, streaming=False),
        )
        try:
            request = sdk["SendMessageRequest"](
                message=sdk["new_text_message"](_message_text(message))
            )
            return await collect_text(client.send_message(request))
        finally:
            close = getattr(client, "close", None)
            if close is not None:
                await close()
            await http_client.aclose()


class OfficialA2ATransport:
    """AsyncA2ATransportPort over the official A2A SDK."""

    satisfies = "AsyncA2ATransportPort"

    def __init__(
        self,
        *,
        endpoint_for: EndpointResolver,
        audience_for: AudienceResolver,
        token_provider: TokenProvider | None = None,
        client: Any | None = None,
        timeout: float = 60.0,
        delegation_chain: Sequence[Mapping[str, Any]] | None = None,
        message_builder: MessageBuilder | None = None,
    ) -> None:
        self._endpoint_for = endpoint_for
        self._audience_for = audience_for
        self._client = client or OfficialA2AClient(token_provider, timeout=timeout)
        self._delegation_chain = [dict(item) for item in (delegation_chain or [])]
        self._message_builder = message_builder or (lambda question: question)

    async def send(self, dst: AgentRef, question: str, scope: Scope) -> str:  # noqa: ARG002
        return await self._client.call(
            agent_id=dst.agent_id,
            endpoint=self._endpoint_for(dst),
            audience=self._audience_for(dst),
            message=self._message_builder(question),
            delegation_chain=list(self._delegation_chain),
        )


# Backwards-compatible adapter name for callers that imported the old stub.
A2ATransport = OfficialA2ATransport
