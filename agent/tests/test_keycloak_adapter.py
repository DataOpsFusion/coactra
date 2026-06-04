import pytest

from coactra.agent import DelegationGrant, Scope, TokenExchanger, TokenPassthroughError
from coactra.agent.adapters.keycloak import (
    AsyncKeycloakExchanger,
    KeycloakExchanger,
    TokenExchangeError,
)


def test_keycloak_exchanger_posts_rfc8693_form_and_returns_only_fresh_token():
    calls = []

    def transport(url, form, headers):
        calls.append((url, form, headers))
        return {"access_token": "fresh-downstream"}

    exchanger = KeycloakExchanger(
        token_endpoint="https://id.example/token",
        client_id="agent-runtime",
        client_secret="secret",
        audience="mcp-api",
        actor_token_factory=lambda: "service-actor-token",
        transport=transport,
    )
    assert isinstance(exchanger, TokenExchanger)
    identity = exchanger.exchange(
        DelegationGrant(
            subject_token="human-secret",
            actor="agent:platform",
            audience="mcp-prod",
            requested_scopes=("tools:call", "memory:read"),
            delegation_chain=["host:homelab"],
        ),
        Scope(tenant_id="acme"),
    )

    _, form, headers = calls[0]
    assert form["grant_type"].endswith("token-exchange")
    assert form["subject_token"] == "human-secret"
    assert form["actor_token"] == "service-actor-token"
    assert form["audience"] == "mcp-prod"
    assert form["scope"] == "tools:call memory:read"
    assert headers["Authorization"].startswith("Basic ")
    assert identity.token == "fresh-downstream"
    assert identity.act_chain == ["host:homelab", "agent:platform"]
    assert "human-secret" not in identity.model_dump_json()


def test_keycloak_exchanger_rejects_as_passthrough_and_malformed_response():
    scope = Scope(tenant_id="acme")
    grant = DelegationGrant(subject_token="subject", actor="agent:x")
    passthrough = KeycloakExchanger(
        token_endpoint="https://id.example/token", client_id="x", transport=lambda *_: {"access_token": "subject"}
    )
    malformed = KeycloakExchanger(
        token_endpoint="https://id.example/token", client_id="x", transport=lambda *_: {}
    )
    with pytest.raises(TokenPassthroughError):
        passthrough.exchange(grant, scope)
    with pytest.raises(TokenExchangeError):
        malformed.exchange(grant, scope)


def test_keycloak_exchange_from_reexchanges_prior_identity_and_extends_chain():
    seen = []

    def transport(url, form, headers):
        seen.append(form["subject_token"])
        return {"access_token": f"fresh-{len(seen)}"}

    exchanger = KeycloakExchanger(token_endpoint="https://id.example/token", client_id="x", transport=transport)
    scope = Scope(tenant_id="acme")
    first = exchanger.exchange(DelegationGrant(subject_token="human", actor="agent:a"), scope)
    second = exchanger.exchange_from(first, actor="agent:b", scope=scope)
    assert seen == ["human", "fresh-1"]
    assert second.act_chain == ["agent:a", "agent:b"]


@pytest.mark.asyncio
async def test_async_keycloak_exchanger_posts_without_blocking_adapter_shape():
    calls = []

    async def transport(url, form, headers):
        calls.append((url, form, headers))
        return {"access_token": "async-fresh"}

    exchanger = AsyncKeycloakExchanger(
        token_endpoint="https://id.example/token",
        client_id="agent-runtime",
        client_secret="secret",
        actor_token="service-actor-token",
        transport=transport,
    )
    identity = await exchanger.exchange(
        DelegationGrant(subject_token="human-secret", actor="agent:platform"),
        Scope(tenant_id="acme"),
    )

    _, form, headers = calls[0]
    assert form["subject_token"] == "human-secret"
    assert form["actor_token"] == "service-actor-token"
    assert headers["Authorization"].startswith("Basic ")
    assert identity.token == "async-fresh"
    assert "human-secret" not in identity.model_dump_json()
