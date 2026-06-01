"""Collaboration policy over A2A — the third session-level gap.

A2A is mature (tasks/multi-turn/streaming/push/artifacts); it does NOT decide WHO may talk
to WHOM, WHEN. That policy is the gap. CollaborationPolicy answers can_talk(src, dst,
scope) purely in-process; PolicyGatedCollaborator gates a real A2A transport behind it so a
denied request never reaches the wire.

DESIGN: collaboration targets are TENANT-QUALIFIED and DENIABLE. A target is an
`AgentRef(tenant_id, agent_id)` — it carries its OWN tenant, so the policy can adjudicate
cross-TENANT talk and DENY it. A bare-string agent id (e.g. a workflow `ask` step's
`agent`) is lifted to an `AgentRef` in the CALLER's tenant (same-tenant-as-scope), so the
intra-tenant path is unchanged while cross-tenant talk becomes expressible and deniable.

Inter-library seam: PolicyGatedCollaborator STRUCTURALLY satisfies fleetlib.workflow's
`Collaborator` (.ask(agent, question, state)) and `EscalationRouter` (.route(escalation,
chain)) Protocols — the talk that workflow's `ask`/`escalate` steps deferred "to the agent
layer". We do not import workflow; structural typing is the contract. The `ask` signature
(name `agent`, arity, return) is preserved; only its first parameter is WIDENED to accept
`str | AgentRef`, which is structurally safe for a runtime_checkable Protocol.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from fleetlib.agent.scope import Scope


class CollaborationDenied(RuntimeError):
    """Raised when policy refuses a talk request before it reaches the transport."""


class AgentRef(BaseModel):
    """A tenant-qualified collaboration / A2A target.

    The target carries its OWN tenant, so a CollaborationPolicy can deny cross-tenant talk.
    """

    model_config = {"frozen": True}

    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)


def _as_ref(target: str | AgentRef, scope: Scope) -> AgentRef:
    """Lift a bare-string agent id into a same-tenant-as-`scope` AgentRef; pass an AgentRef
    through unchanged. A bare string therefore can never trip the cross-tenant gate."""
    if isinstance(target, AgentRef):
        return target
    return AgentRef(tenant_id=scope.tenant_id, agent_id=target)


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


class AllowSameTenant:
    """Default CollaborationPolicy — denies cross-TENANT talk; within one tenant, gates the
    WHO-MAY-TALK-TO-WHOM pair.

    Two layered rules:
      1. Cross-tenant DENIAL (unconditional): if the source and destination tenants differ,
         return False BEFORE any allow-set check. This is the deniable cross-tenant boundary
         — only expressible because a target is an `AgentRef` carrying its own tenant.
      2. Intra-tenant who-may-talk-to-whom:
           - `allowed is None` (default): permit any intra-tenant pair (open default;
             swap a stricter CollaborationPolicy to lock it down).
           - `allowed` given: permit only the listed `(src_agent_id, dst_agent_id)` pairs.
    """

    def __init__(self, allowed: set[tuple[str, str]] | None = None) -> None:
        self._allowed = allowed

    def can_talk(self, src: str | AgentRef, dst: str | AgentRef, scope: Scope) -> bool:
        src_ref = _as_ref(src, scope)
        dst_ref = _as_ref(dst, scope)
        # (1) cross-tenant denial — the deniable boundary the AgentRef makes expressible.
        if src_ref.tenant_id != dst_ref.tenant_id:
            return False
        # (2) intra-tenant who-may-talk-to-whom.
        if self._allowed is None:
            return True
        return (src_ref.agent_id, dst_ref.agent_id) in self._allowed


class PolicyGatedCollaborator:
    """Gates an A2A transport behind a CollaborationPolicy.

    Implements BOTH workflow seams by structural typing:
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
        me_ref = AgentRef(tenant_id=self._scope.tenant_id, agent_id=self._me)
        dst_ref = _as_ref(agent, self._scope)
        if not self._policy.can_talk(me_ref, dst_ref, self._scope):
            raise CollaborationDenied(
                f"{me_ref.tenant_id}/{me_ref.agent_id} -> "
                f"{dst_ref.tenant_id}/{dst_ref.agent_id} denied by policy"
            )
        return self._transport.send(dst_ref, question, self._scope)

    def route(self, escalation: Any, chain: list[str]) -> str:
        """Escalation walks UP the org-provided chain to its terminal decider. The chain
        is opaque to agent (organization owns who-reports-to-whom); we take the last id as
        the terminal decider (human / SOTA), matching the sibling workflow default."""
        if not chain:
            raise CollaborationDenied(getattr(escalation, "reason", "unresolved"))
        return chain[-1]
