import pytest

from coactra.agent import (
    DelegationGrant,
    InProcessExchanger,
    Scope,
    check_token_exchanger_contract,
)


@pytest.mark.asyncio
async def test_token_exchanger_conformance_probe_accepts_inprocess_exchanger():
    report = await check_token_exchanger_contract(
        InProcessExchanger(),
        scope=Scope(tenant_id="acme"),
    )
    assert report.exchanger == "InProcessExchanger"
    assert report.chain_depth == 2


def test_inprocess_exchanger_binds_token_to_subject_token():
    exchanger = InProcessExchanger()
    scope = Scope(tenant_id="acme")

    first = exchanger.exchange(
        DelegationGrant(subject_token="one", actor="agent:contract"),
        scope,
    )
    second = exchanger.exchange(
        DelegationGrant(subject_token="two", actor="agent:contract"),
        scope,
    )

    assert first.token != second.token
