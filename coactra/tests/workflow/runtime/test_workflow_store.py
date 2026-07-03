from coactra.workflow import (
    InMemoryProcedureStore,
    Procedure,
    ProcedureStore,
    Scope,
    Step,
)

ACME = Scope(tenant_id="acme", namespace="agent:1")
GLOBEX = Scope(tenant_id="globex", namespace="agent:1")


def _proc(name="deploy"):
    return Procedure(name=name, steps=[Step(id="a", kind="task")])


def test_store_satisfies_protocol():
    assert isinstance(InMemoryProcedureStore(), ProcedureStore)


def test_save_then_get_in_scope():
    store = InMemoryProcedureStore()
    store.save(_proc(), ACME)
    got = store.get("deploy", ACME)
    assert got is not None and got.name == "deploy"


def test_get_missing_returns_none():
    assert InMemoryProcedureStore().get("nope", ACME) is None


def test_list_returns_scope_procedures_only():
    store = InMemoryProcedureStore()
    store.save(_proc("deploy"), ACME)
    store.save(_proc("backup"), ACME)
    names = {p.name for p in store.list(ACME)}
    assert names == {"deploy", "backup"}


def test_tenant_isolation_is_real():
    store = InMemoryProcedureStore()
    store.save(_proc("acme-only"), ACME)
    assert store.get("acme-only", GLOBEX) is None
    assert store.list(GLOBEX) == []


def test_procedure_round_trips_through_the_store():
    store = InMemoryProcedureStore()
    store.save(_proc("deploy"), ACME)
    got = store.get("deploy", ACME)
    assert got is not None and got.name == "deploy"
