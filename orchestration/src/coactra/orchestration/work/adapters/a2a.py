"""Converters for the official A2A Python SDK.

A2A already defines interoperable Agent Cards, Skills, Parts, and Artifacts. Coactra
keeps its core dependency-light and converts at the network boundary.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

from coactra.orchestration.work.adapters._optional import optional_module
from coactra.orchestration.work.domain.artifacts import Artifact, ArtifactPart
from coactra.orchestration.work.domain.capabilities import AgentSpec, SkillSpec


def _types(module: ModuleType | None) -> ModuleType:
    return module or optional_module("a2a.types", extra="a2a")


def to_a2a_skill(skill: SkillSpec, *, types: ModuleType | None = None) -> Any:
    a2a = _types(types)
    return a2a.AgentSkill(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        tags=skill.tags,
    )


def to_a2a_agent_card(
    spec: AgentSpec,
    *,
    url: str,
    version: str,
    input_modes: list[str] | None = None,
    output_modes: list[str] | None = None,
    streaming: bool = False,
    push_notifications: bool = False,
    state_transition_history: bool = True,
    types: ModuleType | None = None,
) -> Any:
    a2a = _types(types)
    return a2a.AgentCard(
        name=spec.name,
        description=spec.description,
        url=url,
        version=version,
        defaultInputModes=input_modes or ["text/plain"],
        defaultOutputModes=output_modes or ["text/plain", "application/json"],
        capabilities=a2a.AgentCapabilities(
            streaming=streaming,
            pushNotifications=push_notifications,
            stateTransitionHistory=state_transition_history,
        ),
        skills=[to_a2a_skill(skill, types=a2a) for skill in spec.skills],
    )


def to_a2a_artifact(artifact: Artifact, *, types: ModuleType | None = None) -> Any:
    a2a = _types(types)
    return a2a.Artifact(
        artifactId=artifact.id,
        name=artifact.name,
        metadata={
            **artifact.metadata,
            "coactra.provenance": artifact.provenance.model_dump(mode="json"),
        },
        parts=[_to_a2a_part(part, types=a2a) for part in artifact.parts],
    )


def _to_a2a_part(part: ArtifactPart, *, types: ModuleType) -> Any:
    if part.kind == "text":
        root = types.TextPart(text=part.text)
    elif part.kind == "data":
        if not isinstance(part.data, dict):
            raise TypeError("A2A structured data parts must contain a dictionary")
        root = types.DataPart(data=part.data)
    else:
        ref = part.reference
        assert ref is not None
        root = types.FilePart(
            file=types.FileWithUri(uri=ref.uri, mimeType=ref.media_type, name=ref.name)
        )
    return types.Part(root=root)
