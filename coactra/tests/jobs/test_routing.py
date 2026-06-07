import pytest

from coactra.jobs import Scope as WorkScope, WorkManager, WorkOrder
from coactra.jobs.work import InMemoryWorkStore, TenantWorkStoreRouter, WorkStore
from coactra.workflow import (
    AsyncProcedureRunnerAdapter,
    InMemoryProcedureStore,
    Procedure,
    ProcedureRunner,
    ProcedureStore,
    RunContext,
    RunResult,
    Scope,
    Step,
    TenantProcedureStoreRouter,
    TenantWorkflowEngineRouter,
    WorkflowEngine,
)


def test_work_store_router_binds_one_store_per_tenant():
    built = []
    router = TenantWorkStoreRouter(lambda tenant: built.append(tenant) or InMemoryWorkStore())
    assert isinstance(router, WorkStore)
    manager = WorkManager(store=router)
    acme = WorkScope(tenant_id="acme")
    globex = WorkScope(tenant_id="globex")
    order = manager.submit(WorkOrder(scope=acme, title="x"))
    assert manager.get(order.id, acme).title == "x"
    assert manager.list(globex) == []
    assert built == ["acme", "globex"]


def test_procedure_store_router_forwards_full_store_contract():
    router = TenantProcedureStoreRouter(lambda tenant: InMemoryProcedureStore())
    scope = Scope(tenant_id="acme")
    first = Procedure(name="x", steps=[Step(id="a", kind="task")])
    replacement = Procedure(name="x", steps=[Step(id="b", kind="task")])

    assert isinstance(router, ProcedureStore)
    assert router.exists("x", scope) is False
    assert router.delete("x", scope) is False
    router.save(first, scope)
    assert router.exists("x", scope) is True
    router.replace(replacement, scope)
    assert router.get("x", scope) == replacement
    assert router.delete("x", scope) is True
    assert router.get("x", scope) is None


def test_procedure_store_router_binds_one_store_per_tenant():
    built = []
    router = TenantProcedureStoreRouter(lambda tenant: built.append(tenant) or InMemoryProcedureStore())
    procedure = Procedure(name="x", steps=[Step(id="a", kind="task")])
    acme = Scope(tenant_id="acme")
    globex = Scope(tenant_id="globex")
    router.save(procedure, acme)
    assert router.get("x", acme) == procedure
    assert router.get("x", globex) is None
    assert built == ["acme", "globex"]


class Runner:
    def run(self, procedure, state, ctx):
        return RunResult(output=state, path=[procedure.entry.id])


@pytest.mark.asyncio
async def test_workflow_engine_router_routes_thread_to_tenant_runtime():
    built = []
    router = TenantWorkflowEngineRouter(lambda tenant: built.append(tenant) or AsyncProcedureRunnerAdapter(Runner()))
    assert isinstance(router, WorkflowEngine)
    ctx = RunContext(scope=Scope(tenant_id="acme"))
    run = await router.start(Procedure(name="x", steps=[Step(id="a", kind="task")]), {}, ctx, thread_id="t-1")
    assert run.thread_id == "t-1"
    assert built == ["acme"]
