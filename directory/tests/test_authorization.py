from types import SimpleNamespace

import pytest

from coactra.directory import (
    AuthorizationDenied,
    AuthorizationRequest,
    Authorizer,
    InMemoryAuthorizer,
    OpenFGAAuthorizer,
    require_authorized,
)


@pytest.mark.asyncio
async def test_inmemory_authorizer_defaults_to_deny_and_returns_auditable_decisions():
    authorizer = InMemoryAuthorizer()
    request = AuthorizationRequest(
        subject="agent:builder",
        action="deploy",
        resource="project:website",
    )

    denied = await authorizer.check(request)
    assert isinstance(authorizer, Authorizer)
    assert denied.allowed is False
    assert denied.id

    authorizer.grant("agent:builder", "deploy", "project:website")
    allowed = await require_authorized(authorizer, request)
    assert allowed.allowed is True
    assert allowed.source == "inmemory"


@pytest.mark.asyncio
async def test_require_authorized_retains_denied_decision_for_audit():
    with pytest.raises(AuthorizationDenied) as exc:
        await require_authorized(
            InMemoryAuthorizer(),
            AuthorizationRequest(
                subject="agent:junior",
                action="approve",
                resource="deployment:production",
            ),
        )
    assert exc.value.decision.allowed is False
    assert exc.value.decision.id


@pytest.mark.asyncio
async def test_openfga_adapter_maps_generic_request_to_official_sdk_shape():
    calls = []

    class Client:
        async def check(self, *, body):
            calls.append(body)
            return SimpleNamespace(allowed=True, resolution="tuple")

    adapter = OpenFGAAuthorizer(
        Client(),
        request_factory=lambda request: {
            "user": request.subject,
            "relation": request.action,
            "object": request.resource,
            "context": request.context,
        },
    )
    result = await adapter.check(
        AuthorizationRequest(
            subject="agent:builder",
            action="can_deploy",
            resource="project:website",
            context={"environment": "staging"},
        )
    )

    assert calls == [
        {
            "user": "agent:builder",
            "relation": "can_deploy",
            "object": "project:website",
            "context": {"environment": "staging"},
        }
    ]
    assert result.allowed is True
    assert result.source == "openfga"
