"""Team-first API tests.

These tests codify the alpha-breaking Team contract:
- explicit Team scope + policy
- Team-owned agent/skill/workflow catalogs
- exact skill-id routing via match_skill()
- Team.run() as the workflow execution door
"""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team, Workflow
from coactra.agent import Agent
from coactra.agent.skills import Skill
from coactra.workflow import step


@pytest.fixture
def team_scope() -> Scope:
    return Scope(tenant_id="acme", namespace="support")


@pytest.fixture
def permissive_policy():
    return Policy.permissive()


def _team_with_model(scope: Scope, policy, model) -> Team:
    return Team(
        scope=scope,
        policy=policy,
        model_resolver=ModelResolver(
            [ModelRoute(capability="default", profile=ModelProfile(name="default", model=model))]
        ),
    )


def test_team_local_builds_default_scope_policy_and_model_route():
    model = TestModel()

    team = Team.local(model=model, tenant_id="acme", namespace="lazy")

    assert team.scope == Scope(tenant_id="acme", namespace="lazy")
    assert team._model_resolver.route("default").model is model


@pytest.mark.asyncio
async def test_team_local_add_agent_uses_default_model_route():
    team = Team.local(model=TestModel(), tenant_id="acme", namespace="lazy")

    agent = await team.add_agent(name="assistant")

    assert isinstance(agent, Agent)
    assert team.member("assistant") is agent


@pytest.mark.asyncio
async def test_team_add_model_registers_named_model_route(team_scope, permissive_policy):
    model = TestModel()
    team = Team(scope=team_scope, policy=permissive_policy)

    route = team.add_model("smart", model)
    agent = await team.add_agent(name="smart-agent", model_capability="smart")

    assert route.model is model
    assert isinstance(agent, Agent)


class DelegateOnlyDenyPolicy:
    async def check(self, request):
        if request.action == "model.use":
            return await Policy.permissive().check(request)
        if request.action == "agent.delegate":
            return await Policy.default_deny().check(request)
        return await Policy.permissive().check(request)


def test_team_requires_explicit_policy(team_scope):
    with pytest.raises(TypeError):
        Team(scope=team_scope)


def test_team_keeps_scope_and_policy(team_scope, permissive_policy):
    team = Team(scope=team_scope, policy=permissive_policy)

    assert team.scope == team_scope
    assert team.policy is permissive_policy


@pytest.mark.asyncio
async def test_add_agent_registers_runtime_and_member_lookup(team_scope, permissive_policy):
    team = _team_with_model(team_scope, permissive_policy, TestModel())

    agent = await team.add_agent(
        name="sre-agent",
        model_capability="default",
        skills=[Skill("infra.deploy", description="deploy infrastructure")],
        expose=True,
    )

    assert isinstance(agent, Agent)
    assert team.member("sre-agent") is agent


@pytest.mark.asyncio
async def test_add_skill_registers_catalog_entry(team_scope, permissive_policy):
    team = Team(scope=team_scope, policy=permissive_policy)
    skill = Skill("cert.rotate", description="rotate TLS certs")

    team.add_skill(skill)

    assert team.skill("cert.rotate") == skill


@pytest.mark.asyncio
async def test_match_skill_uses_exact_skill_ids(team_scope, permissive_policy):
    team = _team_with_model(team_scope, permissive_policy, TestModel())
    await team.add_agent(
        name="security-agent",
        model_capability="default",
        skills=[Skill("cert.rotate", description="rotate TLS certs")],
        expose=True,
    )
    await team.add_agent(
        name="sre-agent",
        model_capability="default",
        skills=[Skill("infra.deploy", description="deploy infrastructure")],
        expose=True,
    )

    assert team.match_skill("cert.rotate")._name == "security-agent"
    assert team.match_skill("infra.deploy")._name == "sre-agent"
    assert team.match_skill("missing.skill") is None


@pytest.mark.asyncio
async def test_roster_is_derived_from_team_owned_agents(team_scope, permissive_policy):
    team = _team_with_model(team_scope, permissive_policy, TestModel())
    await team.add_agent(
        name="security-agent",
        model_capability="default",
        skills=[Skill("cert.rotate", description="rotate TLS certs")],
        expose=True,
    )

    cards = team.roster()

    assert len(cards) == 1
    assert cards[0]["name"] == "security-agent"
    assert cards[0]["skills"][0]["id"] == "cert.rotate"


@pytest.mark.asyncio
async def test_can_talk_uses_explicit_team_policy(team_scope):
    allow_team = Team(scope=team_scope, policy=Policy.permissive())
    deny_team = Team(scope=team_scope, policy=DelegateOnlyDenyPolicy())

    for current in (allow_team, deny_team):
        current.set_model_routes(
            ModelRoute(
                capability="default", profile=ModelProfile(name="default", model=TestModel())
            )
        )
        await current.add_agent(
            name="a", model_capability="default", skills=[Skill("a")], expose=True
        )
        current.set_model_routes(
            ModelRoute(capability="other", profile=ModelProfile(name="other", model=TestModel()))
        )
        await current.add_agent(
            name="b", model_capability="other", skills=[Skill("b")], expose=True
        )

    assert await allow_team.can_talk("a", "b") is True
    assert await deny_team.can_talk("a", "b") is False


@pytest.mark.asyncio
async def test_add_workflow_registers_catalog_entry(team_scope, permissive_policy):
    team = Team(scope=team_scope, policy=permissive_policy)
    workflow = Workflow("deploy", steps=[step("deploy", agent="sre-agent")])

    team.add_workflow(workflow)

    assert team.workflow("deploy") is workflow


@pytest.mark.asyncio
async def test_team_run_executes_registered_workflow(team_scope, permissive_policy):
    team = _team_with_model(team_scope, permissive_policy, TestModel())
    await team.add_agent(
        name="sre-agent",
        model_capability="default",
        skills=[Skill("infra.deploy", description="deploy infrastructure")],
        expose=True,
    )
    workflow = Workflow("deploy", steps=[step("deploy the service", agent="sre-agent")])
    team.add_workflow(workflow)

    run = await team.run("deploy")

    assert run.status == "completed"
    assert run.results[0].agent == "sre-agent"


def test_team_importable_from_root_and_module():
    import coactra
    import coactra.team as team_mod

    assert coactra.Team is Team
    assert team_mod.Team is Team


@pytest.mark.asyncio
async def test_match_skill_with_required_tags_and_ambiguity(team_scope, permissive_policy):
    team = _team_with_model(team_scope, permissive_policy, TestModel())
    await team.add_agent(
        name="python-impl",
        model_capability="default",
        skills=[Skill("python", tags=["implement", "backend"])],
        expose=True,
    )
    await team.add_agent(
        name="python-security",
        model_capability="default",
        skills=[Skill("python", tags=["security", "review"])],
        expose=True,
    )

    assert team.match_skill("python", required_tags=["security"])._name == "python-security"
    with pytest.raises(ValueError):
        team.match_skill("python")
