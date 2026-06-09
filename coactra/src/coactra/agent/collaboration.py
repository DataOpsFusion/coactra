"""Policy-gated A2A collaboration helpers."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from coactra.agent.domain import AgentRef, Scope, as_ref
from coactra.errors import PermissionDeniedError
from coactra.policy import Policy, PolicyRequest
from coactra.scope import Scope as CoreScope


class CollaborationDenied(PermissionDeniedError):
    """Raised when policy refuses a talk request before it reaches the transport."""


@runtime_checkable
class AsyncA2ATransportPort(Protocol):
    async def send(self, dst: AgentRef, question: str, scope: Scope) -> str:
        """Carry a question over an async A2A client and return the reply."""
        ...


class AsyncNullTransport:
    """Async default A2A transport — no wire configured; returns empty."""

    async def send(self, dst: AgentRef, question: str, scope: Scope) -> str:  # noqa: ARG002
        return ""


def _terminal_route(escalation: Any, chain: list[str]) -> str:
    if not chain:
        raise CollaborationDenied(getattr(escalation, "reason", "unresolved"))
    return chain[-1]


class AsyncPolicyGatedCollaborator:
    """Async collaborator that gates every delegation request behind shared Policy."""

    def __init__(
        self,
        *,
        transport: AsyncA2ATransportPort,
        policy: Policy,
        scope: Scope,
        me: str,
    ) -> None:
        self._transport = transport
        self._policy = policy
        self._scope = scope
        self._me = me

    async def ask(self, agent: str | AgentRef, question: str, state: dict[str, Any]) -> str:  # noqa: ARG002
        me_ref = AgentRef(tenant_id=self._scope.tenant_id, agent_id=self._me)
        dst_ref = as_ref(agent, self._scope)
        decision = await self._policy.check(
            PolicyRequest(
                principal=f"agent:{me_ref.agent_id}",
                action="agent.delegate",
                resource=f"agent:{dst_ref.qualified_name}",
                scope=CoreScope(tenant_id=self._scope.tenant_id, namespace=self._scope.namespace),
                component="agent",
                context={
                    "src_tenant": me_ref.tenant_id,
                    "dst_tenant": dst_ref.tenant_id,
                    "dst_agent": dst_ref.agent_id,
                },
            )
        )
        if not decision.allowed:
            raise CollaborationDenied(
                decision.reason
                or f"{me_ref.qualified_name} -> {dst_ref.qualified_name} denied by policy"
            )
        return await self._transport.send(dst_ref, question, self._scope)

    def route(self, escalation: Any, chain: list[str]) -> str:
        return _terminal_route(escalation, chain)
