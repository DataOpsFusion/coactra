"""Backend-neutral agent capability descriptions and requirements."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CapabilityDescriptor(BaseModel):
    name: str = Field(min_length=1)
    version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CapabilityRequirement(BaseModel):
    name: str = Field(min_length=1)
    required: bool = True


class CapabilitySet(BaseModel):
    items: list[CapabilityDescriptor] = Field(default_factory=list)

    def names(self) -> set[str]:
        return {item.name for item in self.items}

    def satisfies(self, requirements: list[CapabilityRequirement]) -> bool:
        names = self.names()
        return all(
            not requirement.required or requirement.name in names for requirement in requirements
        )


class SkillSpec(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class AgentSpec(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""
    skills: list[SkillSpec] = Field(default_factory=list)
    capabilities: CapabilitySet = Field(default_factory=CapabilitySet)

    def can_accept(self, requirements: list[CapabilityRequirement]) -> bool:
        return self.capabilities.satisfies(requirements)
