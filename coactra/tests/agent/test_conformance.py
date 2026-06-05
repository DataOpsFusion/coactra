import pytest

from coactra.agent import InProcessExchanger, Scope, check_token_exchanger_contract


@pytest.mark.asyncio
async def test_token_exchanger_conformance_probe_accepts_inprocess_exchanger():
    report = await check_token_exchanger_contract(
        InProcessExchanger(),
        scope=Scope(tenant_id="acme"),
    )
    assert report.exchanger == "InProcessExchanger"
    assert report.chain_depth == 2
