"""Reusable contract probes for identity adapters."""

from __future__ import annotations

from pydantic import BaseModel

from coactra.agent.domain import DelegationGrant, Scope
from coactra.agent.identity import (
    AsyncTokenExchanger,
    TokenExchanger,
    as_async_exchanger,
)


class TokenExchangeReport(BaseModel):
    exchanger: str
    chain_depth: int


async def check_token_exchanger_contract(
    exchanger: AsyncTokenExchanger | TokenExchanger,
    *,
    scope: Scope,
) -> TokenExchangeReport:
    """Verify no-passthrough and multi-hop behavior for an identity adapter."""

    async_exchanger: AsyncTokenExchanger = as_async_exchanger(exchanger)
    secret = "contract-subject-token"
    first = await async_exchanger.exchange(
        DelegationGrant(subject_token=secret, actor="agent:contract"),
        scope,
    )
    if first.token == secret or secret in first.model_dump_json():
        raise AssertionError("token exchanger leaked or reused the subject token")
    second = await async_exchanger.exchange_from(
        first,
        actor="agent:reviewer",
        scope=scope,
    )
    if second.act_chain != ["agent:contract", "agent:reviewer"]:
        raise AssertionError("token exchanger failed to preserve delegation chain")
    return TokenExchangeReport(
        exchanger=type(exchanger).__name__,
        chain_depth=second.chain.depth,
    )
