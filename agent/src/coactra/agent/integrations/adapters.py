"""Structural adapters from standalone facades to coactra.agent ports.

Imports of sibling libraries stay lazy where a local scope or runtime context must be
constructed. That keeps this module easy to inspect and keeps the standalone packages
free of reverse dependencies on the integrated stack.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


class AIAdapter:
    """Expose an AI client with ``ask`` and ``structured`` as an agent AIPort."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def ask(self, prompt: str) -> str:
        return self._client.ask(prompt)

    def structured(self, schema: type[Any], prompt: str) -> Any:
        return self._client.structured(schema, prompt)


class MemoryAdapter:
    """Translate agent scope into memory scope before delegating async calls."""

    def __init__(
        self,
        memory: Any,
        *,
        agent: str | None = None,
        session: str | None = None,
        scope_factory: Callable[[Any, str | None, str | None], Any] | None = None,
    ) -> None:
        self._memory = memory
        self._agent = agent
        self._session = session
        self._scope_factory = scope_factory

    def _scope(self, scope: Any) -> Any:
        if self._scope_factory is not None:
            return self._scope_factory(scope, self._agent, self._session)

        from coactra.memory import Scope

        return Scope(
            tenant=scope.tenant_id,
            agent=self._agent or scope.namespace,
            session=self._session,
        )

    async def remember(self, events: Sequence[Any], scope: Any) -> None:
        await self._memory.remember(events, self._scope(scope))

    async def recall(self, query: str, scope: Any, k: int = 10) -> list[Any]:
        return await self._memory.recall(query, self._scope(scope), k)


class WorkspaceAdapter:
    """Expose a scope-bound Workspace facade as an agent WorkspacePort."""

    def __init__(self, workspace: Any) -> None:
        self._workspace = workspace

    def write(self, path: str, data: str) -> None:
        self._workspace.write(path, data)

    def read(self, path: str) -> str:
        return self._workspace.read(path)

    def run(self, command: str | Sequence[str]) -> Any:
        return self._workspace.run(command)


class WorkflowAdapter:
    """Bind a workflow engine to its local scope and runtime handlers."""

    def __init__(
        self,
        engine: Any,
        *,
        scope: Any,
        approver: Any | None = None,
        collaborator: Any | None = None,
        router: Any | None = None,
        chain: Sequence[str] | None = None,
        context_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._engine = engine
        self._scope = scope
        self._approver = approver
        self._collaborator = collaborator
        self._router = router
        self._chain = list(chain or [])
        self._context_factory = context_factory

    def set_collaboration(self, collaborator: Any, *, router: Any | None = None) -> None:
        """Attach the agent's policy-gated collaborator after agent construction."""
        self._collaborator = collaborator
        self._router = router or collaborator

    def _context(self) -> Any:
        kwargs: dict[str, Any] = {"scope": self._scope, "chain": list(self._chain)}
        if self._approver is not None:
            kwargs["approver"] = self._approver
        if self._collaborator is not None:
            kwargs["collaborator"] = self._collaborator
        if self._router is not None:
            kwargs["router"] = self._router
        if self._context_factory is not None:
            return self._context_factory(**kwargs)

        from coactra.workflow import RunContext

        return RunContext(**kwargs)

    def run(self, procedure: Any, state: dict[str, Any]) -> Any:
        return self._engine.run(procedure, state, self._context())


class OrganizationAdapter:
    """Expose an Organization tree root as an agent OrganizationPort."""

    def __init__(self, root: Any) -> None:
        self._root = root

    def can(self, member: Any, action: Any) -> bool:
        return self._root.can(member, action)

    def members(self, node: Any) -> list[Any]:
        return node.members()

    def manager(self, node: Any) -> Any:
        manager = node.manager
        return manager() if callable(manager) else manager


class WorkAdapter:
    """Translate agent scope into work scope for durable work-order lookups."""

    def __init__(
        self,
        work: Any,
        *,
        scope_factory: Callable[[Any], Any] | None = None,
    ) -> None:
        self._work = work
        self._scope_factory = scope_factory

    def _scope(self, scope: Any) -> Any:
        if self._scope_factory is not None:
            return self._scope_factory(scope)

        from coactra.work import Scope

        return Scope(tenant_id=scope.tenant_id, namespace=scope.namespace)

    def submit(self, order: Any) -> Any:
        return self._work.submit(order)

    def get(self, work_id: str, scope: Any) -> Any:
        return self._work.get(work_id, self._scope(scope))

    def cancel(self, work_id: str, scope: Any, *, reason: str = "") -> Any:
        return self._work.cancel(work_id, self._scope(scope), reason=reason)
