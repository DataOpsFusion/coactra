from coactra.memory import check_memory_contract, make_backend


async def test_memory_conformance_probe_accepts_inprocess_backend():
    report = await check_memory_contract(make_backend("inprocess"))
    assert report.backend == "InProcessBackend"
    assert report.recall_count >= 1
    assert report.dump_count >= 1
