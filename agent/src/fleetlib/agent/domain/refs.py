"""AgentRef — a tenant-qualified, deniable collaboration / A2A target.

A target carries its OWN tenant, so a CollaborationPolicy can adjudicate cross-tenant
talk and DENY it. A bare-string agent id (e.g. a workflow `ask` step's `agent`) is lifted
to an AgentRef in the caller's tenant, so the intra-tenant path is unchanged while
cross-tenant talk becomes expressible.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from fleetlib.agent.domain.scope import Scope


class AgentRef(BaseModel):
    """A tenant-qualified collaboration / A2A target.

    The target carries its OWN tenant, so a CollaborationPolicy can deny cross-tenant talk.
    """

    model_config = {"frozen": True}

    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)

    @property
    def qualified_name(self) -> str:
        """`<tenant>/<agent>` — the readable, collision-free identity of the target."""
        return f"{self.tenant_id}/{self.agent_id}"


def as_ref(target: str | AgentRef, scope: Scope) -> AgentRef:
    """Lift a bare-string agent id into a same-tenant-as-`scope` AgentRef; pass an AgentRef
    through unchanged. A bare string therefore can never trip the cross-tenant gate."""
    if isinstance(target, AgentRef):
        return target
    return AgentRef(tenant_id=scope.tenant_id, agent_id=target)
