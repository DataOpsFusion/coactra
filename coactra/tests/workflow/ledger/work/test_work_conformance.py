from coactra.workflow.ledger import InMemoryWorkStore, check_work_store_contract


def test_work_store_conformance_probe_accepts_inmemory_store():
    report = check_work_store_contract(InMemoryWorkStore())
    assert report.backend == "InMemoryWorkStore"
    assert report.events == 1
