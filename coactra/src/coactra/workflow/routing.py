"""Tenant-routed orchestration backends for hard physical silo isolation."""
from __future__ import annotations

from collections.abc import Callable

from coactra._routing import TenantRouter
from coactra.workflow.domain.models import Procedure
from coactra.workflow.domain.scope import Scope
from coactra.workflow.runtime import WorkflowEngine, WorkflowRun
from coactra.workflow.store import ProcedureStore


class TenantProcedureStoreRouter(TenantRouter[ProcedureStore]):
    def save(self, procedure: Procedure, scope: Scope) -> None:
        self.for_tenant(scope.tenant_id).save(procedure, scope)

    def get(self, name: str, scope: Scope) -> Procedure | None:
        return self.for_tenant(scope.tenant_id).get(name, scope)

    def list(self, scope: Scope) -> list[Procedure]:
        return self.for_tenant(scope.tenant_id).list(scope)

    def exists(self, name: str, scope: Scope) -> bool:
        return self.for_tenant(scope.tenant_id).exists(name, scope)

    def replace(self, procedure: Procedure, scope: Scope) -> None:
        self.for_tenant(scope.tenant_id).replace(procedure, scope)

    def delete(self, name: str, scope: Scope) -> bool:
        return self.for_tenant(scope.tenant_id).delete(name, scope)


class TenantWorkflowEngineRouter(TenantRouter[WorkflowEngine]):
    """Route durable workflow execution to one physical runtime client per tenant."""

    def __init__(self, factory: Callable[[str], WorkflowEngine]) -> None:
        super().__init__(factory)
        # Extra index: which tenant owns a given workflow thread (cross-tenant guard).
        self._tenant_by_thread: dict[str, str] = {}

    async def start(self, procedure, state, ctx, *, thread_id=None) -> WorkflowRun:
        run = await self.for_tenant(ctx.scope.tenant_id).start(procedure, state, ctx, thread_id=thread_id)
        self._tenant_by_thread[run.thread_id] = ctx.scope.tenant_id
        return run

    async def resume(
        self, thread_id, ctx, *, procedure=None, decision=None, state=None
    ) -> WorkflowRun:
        tenant_id = self._tenant_by_thread.get(thread_id, ctx.scope.tenant_id)
        if tenant_id != ctx.scope.tenant_id:
            raise ValueError("workflow thread belongs to a different tenant")
        return await self.for_tenant(tenant_id).resume(
            thread_id,
            ctx,
            procedure=procedure,
            decision=decision,
            state=state,
        )
