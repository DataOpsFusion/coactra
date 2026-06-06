"""Keycloak RFC 8693 token-exchange adapter.

The raw subject token is sent only to the authorization server's token endpoint. The
returned ``ExchangedIdentity`` stores the fresh exchanged access token and the immutable
actor chain; it never stores or forwards the original bearer credential.
"""
from __future__ import annotations

import base64
import json
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from coactra.agent.domain import Scope
from coactra.agent.domain.identity import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    TokenPassthroughError,
)
from coactra.agent.errors import AgentError

_TOKEN_EXCHANGE = "urn:ietf:params:oauth:grant-type:token-exchange"
_ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"
Transport = Callable[[str, dict[str, str], dict[str, str]], dict[str, Any]]
AsyncTransport = Callable[[str, dict[str, str], dict[str, str]], Awaitable[dict[str, Any]]]


class TokenExchangeError(AgentError):
    """Raised when the authorization server rejects or malforms an exchange."""


def _post_form(url: str, form: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
    try:
        import httpx
    except ImportError:
        return _post_form_stdlib(url, form, headers)
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, data=form, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise TokenExchangeError(
            f"token exchange failed with HTTP {exc.response.status_code}"
        ) from exc
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise TokenExchangeError(f"token exchange failed: {exc}") from exc


def _post_form_stdlib(url: str, form: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
    request = Request(
        url,
        data=urlencode(form).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded", **headers},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:  # noqa: S310 - configured AS endpoint
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:  # pragma: no cover - exercised by real AS integration tests
        raise TokenExchangeError(f"token exchange failed with HTTP {exc.code}") from exc
    except (URLError, json.JSONDecodeError) as exc:
        raise TokenExchangeError(f"token exchange failed: {exc}") from exc


async def _post_form_async(url: str, form: dict[str, str], headers: dict[str, str]) -> dict[str, Any]:
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - optional extra path
        raise TokenExchangeError("AsyncKeycloakExchanger requires coactra[oauth]") from exc
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, data=form, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise TokenExchangeError(
            f"token exchange failed with HTTP {exc.response.status_code}"
        ) from exc
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise TokenExchangeError(f"token exchange failed: {exc}") from exc


def _basic_auth(client_id: str, client_secret: str) -> str:
    credential = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    return f"Basic {credential}"


def _token_from_response(response: dict[str, Any], subject_token: str) -> str:
    token = response.get("access_token")
    if not isinstance(token, str) or not token:
        raise TokenExchangeError("token exchange response did not contain access_token")
    if token == subject_token:
        raise TokenPassthroughError("authorization server returned the subject token unchanged")
    return token


class KeycloakExchanger:
    """Real RFC 8693 exchanger for Keycloak-compatible token endpoints."""

    satisfies = "TokenExchanger"

    def __init__(
        self,
        *,
        token_endpoint: str,
        client_id: str,
        client_secret: str | None = None,
        audience: str | None = None,
        actor_token: str | None = None,
        actor_token_factory: Callable[[], str] | None = None,
        transport: Transport | None = None,
    ) -> None:
        self._token_endpoint = token_endpoint
        self._client_id = client_id
        self._client_secret = client_secret
        self._audience = audience
        self._actor_token = actor_token
        self._actor_token_factory = actor_token_factory
        self._transport = transport or _post_form

    def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        if grant.passthrough:
            raise TokenPassthroughError("token passthrough is forbidden; exchange instead")
        token = self._exchange_token(
            grant.subject_token,
            audience=grant.audience,
            scopes=grant.requested_scopes,
        )
        chain: Hop | None = None
        for actor in [*grant.delegation_chain, grant.actor]:
            chain = Hop(subject=actor, actor=actor, prev=chain)
        assert chain is not None
        return ExchangedIdentity(
            token=token,
            subject=grant.actor,
            tenant_id=scope.tenant_id,
            chain=chain,
        )

    def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        token = self._exchange_token(identity.token)
        return ExchangedIdentity(
            token=token,
            subject=actor,
            tenant_id=scope.tenant_id,
            chain=identity.chain.extend(subject=identity.subject, actor=actor),
        )

    def _request(
        self,
        subject_token: str,
        *,
        audience: str | None = None,
        scopes: tuple[str, ...] = (),
    ) -> tuple[dict[str, str], dict[str, str]]:
        form = {
            "grant_type": _TOKEN_EXCHANGE,
            "subject_token": subject_token,
            "subject_token_type": _ACCESS_TOKEN,
            "requested_token_type": _ACCESS_TOKEN,
            "client_id": self._client_id,
        }
        if scopes:
            form["scope"] = " ".join(scopes)
        target_audience = audience or self._audience
        actor_token = self._actor_token_factory() if self._actor_token_factory else self._actor_token
        if actor_token:
            form["actor_token"] = actor_token
            form["actor_token_type"] = _ACCESS_TOKEN
        if target_audience:
            form["audience"] = target_audience
        headers: dict[str, str] = {}
        if self._client_secret is not None:
            headers["Authorization"] = _basic_auth(self._client_id, self._client_secret)
        return form, headers

    def _exchange_token(
        self,
        subject_token: str,
        *,
        audience: str | None = None,
        scopes: tuple[str, ...] = (),
    ) -> str:
        form, headers = self._request(subject_token, audience=audience, scopes=scopes)
        response = self._transport(self._token_endpoint, form, headers)
        return _token_from_response(response, subject_token)


class AsyncKeycloakExchanger:
    """Async RFC 8693 exchanger for service runtimes that must not block an event loop."""

    satisfies = "AsyncTokenExchanger"

    def __init__(
        self,
        *,
        token_endpoint: str,
        client_id: str,
        client_secret: str | None = None,
        audience: str | None = None,
        actor_token: str | None = None,
        actor_token_factory: Callable[[], str] | None = None,
        transport: AsyncTransport | None = None,
    ) -> None:
        self._sync = KeycloakExchanger(
            token_endpoint=token_endpoint,
            client_id=client_id,
            client_secret=client_secret,
            audience=audience,
            actor_token=actor_token,
            actor_token_factory=actor_token_factory,
            transport=lambda *_: {},
        )
        self._transport = transport or _post_form_async

    async def exchange(self, grant: DelegationGrant, scope: Scope) -> ExchangedIdentity:
        if grant.passthrough:
            raise TokenPassthroughError("token passthrough is forbidden; exchange instead")
        token = await self._exchange_token(
            grant.subject_token,
            audience=grant.audience,
            scopes=grant.requested_scopes,
        )
        chain: Hop | None = None
        for actor in [*grant.delegation_chain, grant.actor]:
            chain = Hop(subject=actor, actor=actor, prev=chain)
        assert chain is not None
        return ExchangedIdentity(
            token=token,
            subject=grant.actor,
            tenant_id=scope.tenant_id,
            chain=chain,
        )

    async def exchange_from(
        self, identity: ExchangedIdentity, *, actor: str, scope: Scope
    ) -> ExchangedIdentity:
        token = await self._exchange_token(identity.token)
        return ExchangedIdentity(
            token=token,
            subject=actor,
            tenant_id=scope.tenant_id,
            chain=identity.chain.extend(subject=identity.subject, actor=actor),
        )

    async def _exchange_token(
        self,
        subject_token: str,
        *,
        audience: str | None = None,
        scopes: tuple[str, ...] = (),
    ) -> str:
        form, headers = self._sync._request(subject_token, audience=audience, scopes=scopes)
        response = await self._transport(self._sync._token_endpoint, form, headers)
        return _token_from_response(response, subject_token)
