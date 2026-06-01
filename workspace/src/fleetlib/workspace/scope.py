"""Scope — the per-tenant / per-agent desk key threaded through every workspace call.

The charter names the dimensions explicitly: a desk is "per agent/tenant". Isolation is
first-class: a backend roots each desk at <base>/<tenant_id>/<agent_id>/, and nothing
crosses that boundary. agent_id is NOT collapsed into a generic namespace — the per-agent
desk is named in the charter.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scope(BaseModel):
    """Immutable, hashable tenant + agent key for one desk."""

    model_config = {"frozen": True}

    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)

    @property
    def key(self) -> str:
        return f"{self.tenant_id}/{self.agent_id}"
