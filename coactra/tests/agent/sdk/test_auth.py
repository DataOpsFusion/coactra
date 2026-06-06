"""Tests for coactra.agent.sdk.auth — TokenSource, StaticToken, oidc().

TDD: these tests are written RED before auth.py exists.
All HTTP is faked — no network calls.
"""
from __future__ import annotations

import pytest

from coactra.agent.sdk.auth import StaticToken, oidc


# ---------------------------------------------------------------------------
# Test 1: StaticToken returns the fixed value
# ---------------------------------------------------------------------------

async def test_static_token_returns_value() -> None:
    ts = StaticToken("abc")
    assert await ts.token() == "abc"


# ---------------------------------------------------------------------------
# Helpers for oidc() tests
# ---------------------------------------------------------------------------

def make_fake_http(responses: list[dict]) -> tuple[object, list[dict]]:
    """Return a fake http callable and a list that captures call args.

    The fake is an async callable: async (token_url, form) -> dict.
    Responses are consumed in order; repeating the last one if exhausted.
    """
    calls: list[dict] = []

    async def fake_http(token_url: str, form: dict) -> dict:
        calls.append({"token_url": token_url, "form": form})
        idx = min(len(calls) - 1, len(responses) - 1)
        return responses[idx]

    return fake_http, calls


# ---------------------------------------------------------------------------
# Test 2: First call fetches a token
# ---------------------------------------------------------------------------

async def test_oidc_first_call_fetches_token() -> None:
    fake_http, calls = make_fake_http([{"access_token": "t1", "expires_in": 3600}])

    ts = oidc(
        token_url="https://example.com/token",
        client_id="my-client",
        client_secret="secret",
        http=fake_http,
    )

    result = await ts.token()
    assert result == "t1"
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Test 3: Second call within validity window uses cache (no new request)
# ---------------------------------------------------------------------------

async def test_oidc_caches_within_validity_window() -> None:
    fake_http, calls = make_fake_http([{"access_token": "t1", "expires_in": 3600}])

    ts = oidc(
        token_url="https://example.com/token",
        client_id="my-client",
        client_secret="secret",
        http=fake_http,
    )

    first = await ts.token()
    second = await ts.token()
    assert first == "t1"
    assert second == "t1"
    assert len(calls) == 1  # no additional call made


# ---------------------------------------------------------------------------
# Test 4: Refresh after expiry (injectable clock)
# ---------------------------------------------------------------------------

async def test_oidc_refreshes_after_expiry() -> None:
    fake_time = [0.0]  # mutable clock state

    def clock() -> float:
        return fake_time[0]

    fake_http, calls = make_fake_http([
        {"access_token": "t1", "expires_in": 3600},
        {"access_token": "t2", "expires_in": 3600},
    ])

    leeway = 30.0
    ts = oidc(
        token_url="https://example.com/token",
        client_id="my-client",
        client_secret="secret",
        http=fake_http,
        leeway=leeway,
        clock=clock,
    )

    # First fetch at t=0 → t1
    result1 = await ts.token()
    assert result1 == "t1"
    assert len(calls) == 1

    # Advance clock past expiry (expires_in - leeway = 3600 - 30 = 3570 seconds)
    fake_time[0] = 3571.0

    # Should refetch → t2
    result2 = await ts.token()
    assert result2 == "t2"
    assert len(calls) == 2


# ---------------------------------------------------------------------------
# Test 5: Request body contains grant_type and client_id
# ---------------------------------------------------------------------------

async def test_oidc_sends_correct_grant_type_and_client_id() -> None:
    fake_http, calls = make_fake_http([{"access_token": "t1", "expires_in": 3600}])

    ts = oidc(
        token_url="https://example.com/token",
        client_id="my-client",
        client_secret="secret",
        scope="read write",
        http=fake_http,
    )

    await ts.token()

    assert len(calls) == 1
    form = calls[0]["form"]
    assert form["grant_type"] == "client_credentials"
    assert form["client_id"] == "my-client"
    assert form["client_secret"] == "secret"
    assert form["scope"] == "read write"
