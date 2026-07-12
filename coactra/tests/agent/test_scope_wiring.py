from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from coactra import AgentSpec, Policy, Scope, Team
from coactra.agent import Scope as AgentScope
from coactra.agent.facade import build_agent
from coactra.memory import Scope as MemoryScope
from coactra.memory.backends.inprocess import InProcessBackend
from coactra.workflow import Scope as WorkflowScope
from coactra.workflow.ledger import Scope as LedgerScope
from coactra.workflow.ledger.domain.models import WorkOrder
from coactra.workspace import Scope as WorkspaceScope
from coactra.workspace import open_workspace


class _CapturingPolicy:
    def __init__(self) -> None:
        self.requests = []

    async def check(self, request):
        self.requests.append(request)
        return await Policy.permissive().check(request)


def test_all_package_scope_exports_are_the_canonical_scope():
    assert AgentScope is Scope
    assert MemoryScope is Scope
    assert WorkspaceScope is Scope
    assert WorkflowScope is Scope
    assert LedgerScope is Scope


@pytest.mark.asyncio
async def test_team_preserves_explicit_shared_scope_and_policy_sees_it():
    policy = _CapturingPolicy()
    team = Team.local(model=TestModel(), tenant_id="acme", policy=policy)
    shared = Scope(tenant_id="acme", namespace="shared")

    agent = await team.add_agent(AgentSpec(name="shared-agent", scope=shared))

    assert agent.scope == shared
    assert team.spec("shared-agent").scope == shared
    model_request = next(request for request in policy.requests if request.action == "model.use")
    assert model_request.scope == shared


@pytest.mark.asyncio
async def test_build_agent_passes_full_scope_to_memory_binding():
    scope = Scope(
        tenant_id="acme",
        namespace="support",
        agent_id="assistant",
        session_id="session-1",
    )
    backend = InProcessBackend()

    agent = await build_agent(
        AgentSpec(name="assistant", model=TestModel(), scope=scope, memory=backend)
    )

    assert agent.scope == scope
    assert agent._runtime._memory._scope == scope


@pytest.mark.asyncio
async def test_memory_namespace_and_session_do_not_cross_scope():
    backend = InProcessBackend()
    first = Scope(tenant_id="acme", namespace="one", agent_id="assistant")
    second = Scope(tenant_id="acme", namespace="two", agent_id="assistant")

    await backend.remember(["private deployment note"], first)

    assert await backend.recall("deployment note", first)
    assert await backend.recall("deployment note", second) == []


@pytest.mark.asyncio
async def test_memory_shared_pool_uses_agent_id_none():
    backend = InProcessBackend()
    shared = Scope(tenant_id="acme", namespace="team-memory")

    await backend.remember(["shared runbook"], shared)

    assert await backend.recall("shared runbook", shared)


def test_workspace_path_contains_namespace_and_requires_path_safe_scope(tmp_path: Path):
    scope = Scope(tenant_id="acme", namespace="ops", agent_id="builder")
    workspace = open_workspace(scope=scope, base_dir=tmp_path)
    try:
        assert Path(workspace.root).relative_to(tmp_path) == Path("acme/ops/builder")
    finally:
        workspace.close()

    with pytest.raises(ValueError):
        open_workspace(
            scope=Scope(
                tenant_id="acme",
                namespace="department/infrastructure",
                agent_id="builder",
            ),
            base_dir=tmp_path,
        )
    with pytest.raises(ValueError):
        open_workspace(scope=Scope(tenant_id="acme", namespace="ops"), base_dir=tmp_path)


def test_ledger_scope_round_trips_as_the_canonical_dataclass():
    scope = Scope(
        tenant_id="acme",
        namespace="support",
        agent_id="assistant",
        session_id="session-1",
    )
    order = WorkOrder(scope=scope, title="round trip")

    restored = WorkOrder.model_validate(order.model_dump())

    assert restored.scope == scope
    assert type(restored.scope) is Scope
