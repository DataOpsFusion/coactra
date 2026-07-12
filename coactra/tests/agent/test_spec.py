from __future__ import annotations

import dataclasses

import pytest

from coactra import AgentSpec, Scope
from coactra.agent.skills import Skill


def test_agent_spec_minimal_defaults():
    spec = AgentSpec(name="helper")
    assert spec.name == "helper"
    assert spec.model is None
    assert spec.model_capability is None
    assert spec.instructions is None
    assert spec.scope is None
    assert spec.tools == ()
    assert spec.skills == ()
    assert spec.peers == ()
    assert spec.defaults == {}
    assert spec.expose is False
    assert spec.runtime is None


def test_agent_spec_requires_non_empty_name():
    with pytest.raises(ValueError):
        AgentSpec(name="")


def test_agent_spec_normalizes_sequences_and_skills():
    spec = AgentSpec(
        name="helper",
        tools=[print],
        peers=["other"],
        skills=[Skill("python", tags=("implement",)), {"id": "review"}],
        defaults={"gateway": "openai"},
    )
    assert isinstance(spec.tools, tuple)
    assert isinstance(spec.peers, tuple)
    assert [skill.id for skill in spec.skills] == ["python", "review"]
    assert all(isinstance(skill, Skill) for skill in spec.skills)
    assert spec.defaults == {"gateway": "openai"}


def test_agent_spec_accepts_string_skill_shorthand():
    spec = AgentSpec(name="helper", skills="rotate certs")
    assert len(spec.skills) == 1
    assert spec.skills[0].id == "general"


def test_agent_spec_is_frozen_and_replaceable():
    spec = AgentSpec(name="helper")
    with pytest.raises(dataclasses.FrozenInstanceError):
        spec.name = "other"  # type: ignore[misc]
    resolved = dataclasses.replace(
        spec, scope=Scope(tenant_id="acme", agent_id="helper")
    )
    assert resolved.scope is not None
    assert resolved.scope.tenant_id == "acme"
    assert spec.scope is None


def test_agent_spec_is_a_lazy_top_level_export():
    import coactra

    assert "AgentSpec" in coactra.__all__
    assert coactra.AgentSpec is AgentSpec
