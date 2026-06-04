"""Tenant scope threaded through every work operation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Scope(BaseModel):
    """Immutable tenant + namespace key."""

    model_config = {"frozen": True}

    tenant_id: str = Field(min_length=1)
    namespace: str = Field(default="default", min_length=1)

    @property
    def key(self) -> str:
        return f"{self.tenant_id}/{self.namespace}"
