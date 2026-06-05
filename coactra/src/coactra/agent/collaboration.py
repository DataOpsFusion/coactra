"""Collaboration policy over A2A — the third session-level gap.

A2A is mature (tasks/multi-turn/streaming/push/artifacts); it does NOT decide WHO may talk
to WHOM, WHEN. That policy is the gap. CollaborationPolicy answers can_talk(src, dst,
scope) purely in-process; PolicyGatedCollaborator gates a real A2A transport behind it so a
denied request never reaches the wire.

DESIGN: collaboration targets are TENANT-QUALIFIED and DENIABLE. A target is an
`AgentRef(tenant_id, agent_id)` (from `domain.refs`) — it carries its OWN tenant, so the
policy can adjudicate cross-TENANT talk and DENY it. A bare-string agent id (e.g. a
workflow `ask` step's `agent`) is lifted to an `AgentRef` in the caller's tenant.

Inter-library seam: PolicyGatedCollaborator STRUCTURALLY satisfies coactra.jobs.workflow's
`Collaborator` (.ask(agent, question, state)) and `EscalationRouter` (.route(escalation,
chain)) Protocols — verified verbatim against orchestration/workflow/runtime/handlers.py. We do not import
workflow; structural typing is the contract. The `ask` first parameter is WIDENED to
`str | AgentRef`, which is structurally safe for a runtime_checkable Protocol.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from coactra.agent.domain import AgentRef, Scope, as_ref


class CollaborationDenied(RuntimeError):
    """Raised when policy refuses a talk request before it reaches the transport."""


@runtime_checkable
class CollaborationPolicy(Protocol):
    def can_talk(self, src: str | AgentRef, dst: str | AgentRef, scope: Scope) -> bool:
        """Decide whether `src` may collaborate with `dst` within `scope`."""
        ...


@runtime_checkable
class A2ATransportPort(Protocol):
    def send(self, dst: AgentRef, question: str, scope: Scope) -> str:
        """Carry a question to `dst` (a tenant-qualified target) over A2A and return the reply."""
        ...


@runtime_checkable
class AsyncA2ATransportPort(Protocol):
    async def send(self, dst: AgentRef, question: str, scope: Scope) -> str:
        """Carry a question over an async A2A client and return the reply."""
        ...


class AllowSameTenant:
    """Default CollaborationPolicy — denies cross-TENANT talk; within one tenant, gates the
    WHO-MAY-TALK-TO-WHOM pair (deny-before-allow).

    Two layered rules, in order:
      1. Cross-tenant DENIAL (unconditional, evaluated FIRST): if source and destination
         tenants differ, return False before any allow-set check. This is the deniable
         cross-tenant boundary — only expressible because a target is an `AgentRef`
         carrying its own tenant.
      2. Intra-tenant who-may-talk-to-whom:
           - `allowed is None` (default): permit any intra-tenant pair (open default).
           - `allowed` given: permit only the listed `(src_agent_id, dst_agent_id)` pairs.
    """

    def __init__(self, allowed: set[tuple[str, str]] | None = None) -> None:
        self._allowed = allowed

    def can_talk(self, src: str | AgentRef, dst: str | AgentRef, scope: Scope) -> bool:
        src_ref = as_ref(src, scope)
        dst_ref = as_ref(dst, scope)
        # (1) cross-tenant denial — deny-before-allow.
        if src_ref.tenant_id != dst_ref.tenant_id:
            return False
        # (2) intra-tenant who-may-talk-to-whom.
        if self._allowed is None:
            return True
        return (src_ref.agent_id, dst_ref.agent_id) in self._allowed


class NullTransport:
    """Default A2A transport — no wire configured; records nothing, returns empty."""

    def send(self, dst: AgentRef, question: str, scope: Scope) -> str:
        return ""


class AsyncNullTransport:
    """Async default A2A transport — no wire configured; returns empty."""

    async def send(self, dst: AgentRef, question: str, scope: Scope) -> str:
        return ""


def _allowed_target(
    *,
    policy: CollaborationPolicy,
    scope: Scope,
    me: str,
    agent: str | AgentRef,
) -> AgentRef:
    me_ref = AgentRef(tenant_id=scope.tenant_id, agent_id=me)
    dst_ref = as_ref(agent, scope)
    if not policy.can_talk(me_ref, dst_ref, scope):
        raise CollaborationDenied(
            f"{me_ref.qualified_name} -> {dst_ref.qualified_name} denied by policy"
        )
    return dst_ref


def _terminal_route(escalation: Any, chain: list[str]) -> str:
    if not chain:
        raise CollaborationDenied(getattr(escalation, "reason", "unresolved"))
    return chain[-1]


class PolicyGatedCollaborator:
    """Gates an A2A transport behind a CollaborationPolicy.

    Implements BOTH workflow seams by structural typing (signatures verified against
    coactra.jobs.workflow.handlers):
      ask(agent, question, state) -> str          (workflow.Collaborator)
      route(escalation, chain) -> decider id       (workflow.EscalationRouter)

    The `agent` argument may be a bare string (workflow path — lifted to a same-tenant
    AgentRef) or a tenant-qualified AgentRef (cross-tenant-deniable path). The resolved
    AgentRef is what the transport receives, so the A2A target always carries its tenant.
    """

    def __init__(
        self,
        *,
        transport: A2ATransportPort,
        policy: CollaborationPolicy,
        scope: Scope,
        me: str,
    ) -> None:
        self._transport = transport
        self._policy = policy
        self._scope = scope
        self._me = me

    def ask(self, agent: str | AgentRef, question: str, state: dict[str, Any]) -> str:
        dst_ref = _allowed_target(
            policy=self._policy, scope=self._scope, me=self._me, agent=agent
        )
        return self._transport.send(dst_ref, question, self._scope)

    def route(self, escalation: Any, chain: list[str]) -> str:
        """Escalation walks UP the org-provided chain to its terminal decider. The chain
        is opaque to agent (organization owns who-reports-to-whom); we take the last id as
        the terminal decider (human / SOTA), matching the sibling workflow default
        (TerminalHumanRouter)."""
        return _terminal_route(escalation, chain)


class AsyncPolicyGatedCollaborator:
    """Async counterpart for hosts backed by an async A2A SDK client.

    The sync collaborator remains the workflow-compatible default. This form keeps the
    same tenant-qualified deny-before-wire policy while awaiting an async transport.
    """

    def __init__(
        self,
        *,
        transport: AsyncA2ATransportPort,
        policy: CollaborationPolicy,
        scope: Scope,
        me: str,
    ) -> None:
        self._transport = transport
        self._policy = policy
        self._scope = scope
        self._me = me

    async def ask(self, agent: str | AgentRef, question: str, state: dict[str, Any]) -> str:
        dst_ref = _allowed_target(
            policy=self._policy, scope=self._scope, me=self._me, agent=agent
        )
        return await self._transport.send(dst_ref, question, self._scope)

    def route(self, escalation: Any, chain: list[str]) -> str:
        return _terminal_route(escalation, chain)
