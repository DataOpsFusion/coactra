from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from coactra import Policy, Scope, Team
from coactra.agent.skills import Skill
from coactra.model import ModelProfile, ModelResolver, ModelRoute


@pytest.fixture
def team_scope() -> Scope:
    return Scope(tenant_id="acme", namespace="support")


@pytest.mark.asyncio
async def test_model_resolver_allows_registered_capability(team_scope):
    resolver = ModelResolver(
        [
            ModelRoute(
                capability="fast-chat",
                profile=ModelProfile(name="default-fast", model=TestModel()),
            )
        ]
    )

    route = await resolver.resolve(
        "fast-chat",
        principal="agent:triage",
        scope=team_scope,
        policy=Policy.permissive(),
    )

    assert route.capability == "fast-chat"
    assert isinstance(route.model, TestModel)
    assert route.profile.name == "default-fast"


@pytest.mark.asyncio
async def test_model_resolver_denies_when_policy_denies(team_scope):
    resolver = ModelResolver(
        [
            ModelRoute(
                capability="fast-chat",
                profile=ModelProfile(name="default-fast", model=TestModel()),
            )
        ]
    )

    with pytest.raises(PermissionError):
        await resolver.resolve(
            "fast-chat",
            principal="agent:triage",
            scope=team_scope,
            policy=Policy.default_deny(),
        )


@pytest.mark.asyncio
async def test_team_add_agent_accepts_model_capability(team_scope):
    model = TestModel()
    team = Team(
        scope=team_scope,
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(
                    capability="fast-chat",
                    profile=ModelProfile(name="default-fast", model=model),
                )
            ]
        ),
    )

    agent = await team.add_agent(
        name="triage-agent",
        model_capability="fast-chat",
        skills=[Skill("incident.triage")],
        expose=True,
    )

    assert team.member("triage-agent") is agent
    assert team._agent_specs["triage-agent"].model_capability == "fast-chat"
    assert agent._runtime._model is model
