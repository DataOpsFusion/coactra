"""Tests for coactra.agent.auth — TokenSource and StaticToken."""

from __future__ import annotations

from coactra.agent.auth import StaticToken


async def test_static_token_returns_value() -> None:
    ts = StaticToken("abc")
    assert await ts.token() == "abc"
