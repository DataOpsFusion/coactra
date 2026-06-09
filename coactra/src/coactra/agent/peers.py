"""Outbound peer delegation tool factory."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from coactra.agent.collaboration import (
    AsyncPolicyGatedCollaborator,
    CollaborationDenied,
)
from coactra.agent.domain import AgentRef, Scope
from coactra.policy import Policy, PolicyRequest
from coactra.scope import Scope as CoreScope

__all__ = ["RemotePeer", "peer_tools"]


@dataclass(frozen=True)
class RemotePeer:
    """Public config for a remote A2A peer exposed through Team-built agents."""

    name: str
    endpoint: str
    audience: str | None = None
    tenant: str | None = None
    token_provider: Any | None = None
    client: Any | None = None
    timeout: float = 60.0
    delegation_chain: Sequence[Mapping[str, Any]] | None = None
    message_builder: Any | None = None

    @property
    def ref(self) -> AgentRef:
        return AgentRef(tenant_id=self.tenant or "default", agent_id=self.name)

    def transport(self) -> Any:
        from coactra.agent.adapters.a2a import OfficialA2ATransport  # noqa: PLC0415

        return OfficialA2ATransport(
            endpoint_for=lambda _dst: self.endpoint,
            audience_for=lambda _dst: self.audience or self.endpoint,
            token_provider=self.token_provider,
            client=self.client,
            timeout=self.timeout,
            delegation_chain=self.delegation_chain,
            message_builder=self.message_builder,
        )


def peer_tools(
    peers: Sequence[str | AgentRef],
    resolve: Callable[[str], Any | None],
    *,
    policy: Policy,
    transport: Any | None = None,
    me: str | None = None,
    tenant: str | None = None,
) -> list[Callable]:
    """Turn peer names into async delegation tools."""
    effective_me = me or "agent"
    effective_tenant = tenant or "default"

    tools: list[Callable] = []
    for name in peers:
        tools.append(
            _make_peer_tool(
                name=name,
                resolve=resolve,
                policy=policy,
                transport=transport,
                me=effective_me,
                tenant=effective_tenant,
            )
        )
    return tools


def _make_peer_tool(
    *,
    name: str | AgentRef,
    resolve: Callable[[str], Any | None],
    policy: Policy,
    transport: Any | None,
    me: str,
    tenant: str,
) -> Callable:
    peer_id = name.agent_id if isinstance(name, AgentRef) else name
    remote_ref = (
        name if isinstance(name, AgentRef) else AgentRef(tenant_id=tenant, agent_id=peer_id)
    )
    tool_name = "ask_" + peer_id.replace("-", "_")
    caller_scope = Scope(tenant_id=tenant)

    async def _tool(question: str) -> str:
        peer = resolve(peer_id)
        if peer is None:
            if transport is None:
                return f"not found: peer '{peer_id}' is unavailable in this team"
            collaborator = AsyncPolicyGatedCollaborator(
                transport=transport,
                policy=policy,
                scope=caller_scope,
                me=me,
            )
            try:
                return await collaborator.ask(remote_ref, question, {})
            except CollaborationDenied as exc:
                return f"not permitted: {exc}"

        src_ref = AgentRef(tenant_id=tenant, agent_id=me)
        peer_tenant = getattr(peer, "_tenant", tenant)
        resolved_peer_id = getattr(peer, "_name", peer_id)
        dst_ref = AgentRef(tenant_id=peer_tenant, agent_id=resolved_peer_id)
        decision = await policy.check(
            PolicyRequest(
                principal=f"agent:{src_ref.agent_id}",
                action="agent.delegate",
                resource=f"agent:{dst_ref.qualified_name}",
                scope=CoreScope(tenant_id=caller_scope.tenant_id, namespace=caller_scope.namespace),
                component="agent",
                context={
                    "src_tenant": src_ref.tenant_id,
                    "dst_tenant": dst_ref.tenant_id,
                    "dst_agent": dst_ref.agent_id,
                },
            )
        )
        if not decision.allowed:
            denied = (
                decision.reason
                or (
                    f"delegation from '{src_ref.qualified_name}' "
                    f"to '{dst_ref.qualified_name}' denied by policy"
                )
            )
            return "not permitted: " + denied

        return await peer.run(question)

    _tool.__name__ = tool_name
    _tool.__qualname__ = tool_name
    return _tool
