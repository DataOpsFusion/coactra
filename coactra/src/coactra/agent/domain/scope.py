"""Scope — the tenant-scoped key threaded through every subsystem of the agent.

Defined LOCALLY (these are standalone distributions; no cross-library import). Same shape
as every sibling library: tenant_id + namespace. Isolation is first-class — a mount, a
delegation, and a collaboration check all carry a Scope, and nothing crosses a
(tenant_id, namespace) boundary unless code explicitly moves it.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scope(BaseModel):
    """Immutable, hashable tenant + namespace key."""

    model_config = {"frozen": True}

    tenant_id: str = Field(min_length=1)
    namespace: str = Field(default="default", min_length=1)

    @property
    def key(self) -> str:
        return f"{self.tenant_id}/{self.namespace}"
