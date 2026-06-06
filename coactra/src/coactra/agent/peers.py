"""Outbound peer delegation — in-process A2A tool factory.

``peer_tools`` turns a list of peer names into async delegation tools that an
agent can call via its normal tool mechanism.  Each tool wraps an in-process
``agent.run`` call gated behind a ``CollaborationPolicy``.

Remote-A2A delegation over ``OfficialA2ATransport`` is a natural follow-on
variant: replace the in-process ``peer.run`` call with a transport send and
wrap it in ``AsyncPolicyGatedCollaborator``.  That path is not built here to
keep this module dependency-free from the A2A client SDK.

Public API
----------
- ``peer_tools`` — build a list of async delegation tools from peer names.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from coactra.agent.collaboration import AllowSameTenant
from coactra.agent.domain import AgentRef, Scope

__all__ = ["peer_tools"]


def peer_tools(
    peers: list[str],
    resolve: Callable[[str], Any | None],
    *,
    policy: Any | None = None,
    me: str | None = None,
    tenant: str | None = None,
) -> list[Callable]:
    """Turn peer names into async delegation tools.

    For each name in *peers*, produce an async callable ``ask_<name>`` that,
    when invoked with a *question* string:

    1. Resolves the peer via ``resolve(name)``.
    2. Checks that the resolved peer's tenant matches the caller's tenant via
       *policy* (defaults to ``AllowSameTenant``).
    3. Calls ``peer.run(question)`` and returns the text reply.

    Parameters
    ----------
    peers:
        Ordered list of peer agent names to wrap.
    resolve:
        Callable ``resolve(name) -> Agent | None`` — looks up a peer in the
        in-process registry (e.g. ``Team.member``).
    policy:
        A ``CollaborationPolicy`` instance.  Defaults to
        ``AllowSameTenant()`` (any intra-tenant pair is permitted; all
        cross-tenant talk is denied before the wire).
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
            me=effective_me,
            tenant=effective_tenant,
        )
        tools.append(tool)

    return tools


def _make_peer_tool(
    *,
    name: str,
    resolve: Callable[[str], Any | None],
    policy: Any,
    me: str,
    tenant: str,
) -> Callable:
    """Build and return a single ``ask_<name>`` async callable."""
    tool_name = "ask_" + name.replace("-", "_")
    caller_scope = Scope(tenant_id=tenant)

    async def _tool(question: str) -> str:
        peer = resolve(name)
        if peer is None:
            return f"not found: peer '{name}' is unavailable in this team"

        # Build tenant-qualified refs so the policy can adjudicate
        # cross-tenant talk (a bare string dst would be lifted into the
        # caller's tenant and could never trip the cross-tenant gate).
        src_ref = AgentRef(tenant_id=tenant, agent_id=me)
        peer_tenant = getattr(peer, "_tenant", tenant)
        peer_id = getattr(peer, "_name", name)
        dst_ref = AgentRef(tenant_id=peer_tenant, agent_id=peer_id)

        if not policy.can_talk(src_ref, dst_ref, caller_scope):
            return (
                f"not permitted: delegation from '{src_ref.qualified_name}' "
                f"to '{dst_ref.qualified_name}' denied by policy"
            )

        return await peer.run(question)

    _tool.__name__ = tool_name
    _tool.__qualname__ = tool_name
    return _tool
