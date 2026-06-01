"""Composition helper for the complete coactra stack."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from coactra.agent.integrations.adapters import (
    AIAdapter,
    MemoryAdapter,
    OrganizationAdapter,
    WorkflowAdapter,
    WorkspaceAdapter,
)


def _workflow_scope_from_agent(scope: Any) -> Any:
    from coactra.workflow import Scope

    return Scope(tenant_id=scope.tenant_id, namespace=scope.namespace)


def make_coactra_agent(
    *,
    scope: Any,
    ai: Any,
    memory: Any,
    workspace: Any,
    workflow_engine: Any,
    organization: Any,
    workflow_scope: Any | None = None,
    workflow_chain: Sequence[str] | None = None,
    workflow_approver: Any | None = None,
    workflow_context_factory: Any | None = None,
    memory_agent: str | None = None,
    memory_session: str | None = None,
    memory_scope_factory: Any | None = None,
    **agent_kwargs: Any,
) -> Any:
    """Build an Agent over real sibling facades while preserving library boundaries."""
    from coactra.agent import make_agent

    workflow = WorkflowAdapter(
        workflow_engine,
        scope=workflow_scope or _workflow_scope_from_agent(scope),
        approver=workflow_approver,
        chain=workflow_chain,
        context_factory=workflow_context_factory,
    )
    agent = make_agent(
        scope=scope,
        ai=AIAdapter(ai),
        memory=MemoryAdapter(
            memory,
            agent=memory_agent,
            session=memory_session,
            scope_factory=memory_scope_factory,
        ),
        workspace=WorkspaceAdapter(workspace),
        workflow=workflow,
        organization=OrganizationAdapter(organization),
        **agent_kwargs,
    )
    workflow.set_collaboration(agent.collaborator)
    return agent
