import pytest

from coactra.agent import (
    AsyncTokenExchanger,
    CachedAsyncTokenExchanger,
    DelegationGrant,
    ExchangedIdentity,
    InProcessExchanger,
    Scope,
)


class Clock:
    def __init__(self) -> None:
        self.now = 1.0

    def __call__(self) -> float:
        return self.now


@pytest.mark.asyncio
async def test_cached_async_exchanger_wraps_sync_exchanger_and_hides_subject_token():
    clock = Clock()
    exchanger = CachedAsyncTokenExchanger(
        InProcessExchanger(),
        ttl_seconds=10,
        clock=clock,
    )
    grant = DelegationGrant(
        subject_token="human-secret",
        actor="agent:builder",
        audience="mcp-gateway",
        requested_scopes=("tools:call",),
    )
    scope = Scope(tenant_id="acme")

    assert isinstance(exchanger, AsyncTokenExchanger)
    first = await exchanger.exchange(grant, scope)
    second = await exchanger.exchange(grant, scope)

    assert first is second
    assert isinstance(first, ExchangedIdentity)
    assert "human-secret" not in first.model_dump_json()

    clock.now += 11
    refreshed = await exchanger.exchange(grant, scope)
    assert refreshed is not first


@pytest.mark.asyncio
async def test_cached_exchange_from_uses_prior_token_hash_without_passthrough():
    exchanger = CachedAsyncTokenExchanger(InProcessExchanger())
    scope = Scope(tenant_id="acme")
    first = await exchanger.exchange(
        DelegationGrant(subject_token="human", actor="agent:builder"),
        scope,
    )

    second = await exchanger.exchange_from(first, actor="agent:security", scope=scope)
    cached = await exchanger.exchange_from(first, actor="agent:security", scope=scope)

    assert cached is second
    assert second.act_chain == ["agent:builder", "agent:security"]
    assert second.token != first.token
