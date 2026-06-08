"""Typed references to the outputs produced by work."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ArtifactRef(BaseModel):
    """A reference to content held by an external artifact store."""

    uri: str = Field(min_length=1)
    media_type: str = "application/octet-stream"
    name: str | None = None


class ArtifactPart(BaseModel):
    """One text, structured-data, or external-reference part of an artifact."""

    kind: Literal["text", "data", "reference"]
    text: str | None = None
    data: Any | None = None
    reference: ArtifactRef | None = None

    @model_validator(mode="after")
    def _validate_payload(self) -> ArtifactPart:
        payloads = {
            "text": self.text,
            "data": self.data,
            "reference": self.reference,
        }
        if payloads[self.kind] is None:
            raise ValueError(f"{self.kind} artifact part requires {self.kind}")
        if sum(value is not None for value in payloads.values()) != 1:
            raise ValueError("artifact part must contain exactly one payload")
        return self


class Provenance(BaseModel):
    """Lineage for an artifact without leaking a storage-engine object."""

    created_by: str | None = None
    source_work_id: str | None = None
    source_attempt_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    """A typed work output. Large payloads should use ``ArtifactRef``."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    name: str = Field(min_length=1)
    parts: list[ArtifactPart] = Field(min_length=1)
    provenance: Provenance = Field(default_factory=Provenance)
    metadata: dict[str, Any] = Field(default_factory=dict)
