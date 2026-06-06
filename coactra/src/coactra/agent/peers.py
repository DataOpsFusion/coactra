"""Outbound peer delegation tool factory.

``peer_tools`` turns peer names or refs into async delegation tools that an
agent can call via its normal tool mechanism.  Resolved peers use an
in-process ``agent.run`` call; unresolved peers can be sent over a supplied
A2A transport such as ``OfficialA2ATransport``.  Both paths are gated behind a
``CollaborationPolicy`` before any local call or remote wire send.

Public API
----------
- ``peer_tools`` — build a list of async delegation tools from peer names.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coactra.agent.collaboration import (
    AllowSameTenant,
    AsyncPolicyGatedCollaborator,
    CollaborationDenied,
)
from coactra.agent.domain import AgentRef, Scope

__all__ = ["peer_tools"]


def peer_tools(
    peers: list[str | AgentRef],
    resolve: Callable[[str], Any | None],
    *,
    policy: Any | None = None,
    transport: Any | None = None,
    me: str | None = None,
    tenant: str | None = None,
) -> list[Callable]:
    """Turn peer names into async delegation tools.

    For each peer in *peers*, produce an async callable ``ask_<name>`` that,
    when invoked with a *question* string:

    1. Resolves the peer via ``resolve(agent_id)``.
    2. Checks the caller and target via *policy* (defaults to
       ``AllowSameTenant``).
    3. Calls local ``peer.run(question)`` when resolved, or sends over
       *transport* when unresolved and a transport is configured.

    Parameters
    ----------
    peers:
        Ordered list of peer agent names or tenant-qualified ``AgentRef`` targets
        to wrap.
    resolve:
        Callable ``resolve(name) -> Agent | None`` — looks up a peer in the
        in-process registry (e.g. ``Team.member``).
    policy:
        A ``CollaborationPolicy`` instance.  Defaults to
        ``AllowSameTenant()`` (any intra-tenant pair is permitted; all
        cross-tenant talk is denied before the wire).
    transport:
        Optional async A2A transport, for example ``OfficialA2ATransport``.
        Used only when ``resolve(agent_id)`` returns ``None``.
    me:
        The caller's agent id used for policy evaluation.  Defaults to
        ``"agent"`` when not provided.
    tenant:
        The caller's tenant id.  Defaults to ``"default"`` when not provided.

    Returns
    -------
    list[Callable]
        One async callable per peer name; each is named ``ask_<peer_name>``
        with hyphens replaced by underscores.
    """
    effective_policy = policy if policy is not None else AllowSameTenant()
    effective_me = me or "agent"
    effective_tenant = tenant or "default"

    tools: list[Callable] = []

    for name in peers:
        # Use a factory to capture `name` correctly in the closure — a bare
        # loop variable would capture the last iteration value for every tool.
        tool = _make_peer_tool(
            name=name,
            resolve=resolve,
            policy=effective_policy,
            transport=transport,
            me=effective_me,
            tenant=effective_tenant,
        )
        tools.append(tool)

    return tools


def _make_peer_tool(
    *,
    name: str | AgentRef,
    resolve: Callable[[str], Any | None],
    policy: Any,
    transport: Any | None,
    me: str,
    tenant: str,
) -> Callable:
    """Build and return a single ``ask_<name>`` async callable."""
    peer_id = name.agent_id if isinstance(name, AgentRef) else name
    remote_ref = (
        name if isinstance(name, AgentRef)
        else AgentRef(tenant_id=tenant, agent_id=peer_id)
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

        # Build tenant-qualified refs so the policy can adjudicate
        # cross-tenant talk (a bare string dst would be lifted into the
        # caller's tenant and could never trip the cross-tenant gate).
        src_ref = AgentRef(tenant_id=tenant, agent_id=me)
        peer_tenant = getattr(peer, "_tenant", tenant)
        resolved_peer_id = getattr(peer, "_name", peer_id)
        dst_ref = AgentRef(tenant_id=peer_tenant, agent_id=resolved_peer_id)

        if not policy.can_talk(src_ref, dst_ref, caller_scope):
            return (
                f"not permitted: delegation from '{src_ref.qualified_name}' "
                f"to '{dst_ref.qualified_name}' denied by policy"
            )

        return await peer.run(question)

    _tool.__name__ = tool_name
    _tool.__qualname__ = tool_name
    return _tool
