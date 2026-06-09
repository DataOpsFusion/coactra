"""Model routing data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """Concrete model execution profile."""

    name: str
    model: Any
    api_base: str | None = None
    api_key: str | None = None
    defaults: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ModelRoute:
    """Map a requested capability to a concrete model profile."""

    capability: str
    profile: ModelProfile
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def model(self) -> Any:
        return self.profile.model

    @property
    def api_base(self) -> str | None:
        return self.profile.api_base

    @property
    def api_key(self) -> str | None:
        return self.profile.api_key

    @property
    def defaults(self) -> dict[str, Any]:
        return dict(self.profile.defaults)
