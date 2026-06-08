"""Minimal outbound A2A transport over the official a2a-sdk.

Hosts supply endpoint/audience resolution and optional token providers.
For inbound A2A serving, use the a2a-sdk server APIs directly.
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
        raise RuntimeError("coactra[a2a] is required for OfficialA2AClient") from exc
    return {
        "httpx": httpx,
        "ClientConfig": ClientConfig,
        "create_client": create_client,
        "get_message_text": get_message_text,
        "new_text_message": new_text_message,
        "SendMessageRequest": SendMessageRequest,
    }


async def collect_text(responses: AsyncIterator[Any]) -> str:
    """Collect SDK send_message responses into a single de-duplicated string."""
    sdk = _require_a2a_sdk()
    get_text = sdk["get_message_text"]
    seen: list[str] = []
    async for item in responses:
        candidates = list(item) if isinstance(item, tuple) else [item]
        for candidate in candidates:
            try:
                text = get_text(candidate)
            except Exception:  # noqa: BLE001 - not every SDK shape is a Message.
                text = ""
            if text and text not in seen:
                seen.append(text)
    return "\n".join(seen)


def _message_text(message: str | Mapping[str, Any]) -> str:
    if isinstance(message, str):
        return message
    return json.dumps(message)


class OfficialA2AClient:
    """Small official-SDK outbound caller."""

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
        agent_id: str,  # noqa: ARG002 - useful for fakes and logs.
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


A2ATransport = OfficialA2ATransport
