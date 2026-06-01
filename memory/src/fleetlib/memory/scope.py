"""Scope — the tenant-scoped key threaded through every memory call.

Isolation is first-class: nothing crosses a (tenant_id, namespace) boundary unless an
explicit export moves it. namespace lets one tenant partition memory (per-agent,
per-session, shared) without leaking across tenants.
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
