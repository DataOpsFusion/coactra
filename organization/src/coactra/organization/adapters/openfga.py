"""OpenFGA SDK bridge for relationship-based authorization checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coactra.organization.authorization import (
    AuthorizationDecision,
    AuthorizationRequest,
)
from coactra.organization.errors import MissingExtraError

RequestFactory = Callable[[AuthorizationRequest], Any]


def _sdk_request(request: AuthorizationRequest) -> Any:
    try:
        from openfga_sdk.client.models import ClientCheckRequest
    except ImportError as exc:  # pragma: no cover - depends on optional installation
        raise MissingExtraError(
            "OpenFGAAuthorizer requires coactra-organization[openfga]"
        ) from exc
    return ClientCheckRequest(
        user=request.subject,
        relation=request.action,
        object=request.resource,
        context=request.context,
    )


class OpenFGAAuthorizer:
    """Translate the local authorization port into the official OpenFGA SDK.

    The caller owns the SDK client's lifecycle so one configured, connection-pooled
    client can be reused across checks.
    """

    def __init__(
        self,
        client: Any,
        *,
        request_factory: RequestFactory | None = None,
    ) -> None:
        self._client = client
        self._request_factory = request_factory or _sdk_request

    async def check(self, request: AuthorizationRequest) -> AuthorizationDecision:
        response = await self._client.check(body=self._request_factory(request))
        return AuthorizationDecision(
            allowed=bool(response.allowed),
            source="openfga",
            metadata={"resolution": getattr(response, "resolution", "")},
        )
