"""TDD tests for planner — plan_playbook turns a goal + Team into a Playbook."""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope
from coactra.agent.skills import Skill
from coactra.team import Team
from coactra.workflow.playbook import Playbook, Step


class FakeClient:
    def __init__(self, response):
        self._response = response
        self.last_prompt: str = ""

    def structured(self, schema, prompt, **kwargs):
        self.last_prompt = prompt
        return self._response


@pytest.fixture
async def team():
    team = Team(
        scope=Scope(tenant_id="acme", namespace="ops"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [
                ModelRoute(capability="cert", profile=ModelProfile(name="cert", model=TestModel())),
                ModelRoute(
                    capability="deploy", profile=ModelProfile(name="deploy", model=TestModel())
                ),
            ]
        ),
    )
    await team.add_agent(
        name="cert-agent",
        model_capability="cert",
        skills=[Skill("cert.rotate", description="rotate TLS certificates", tags=["cert", "tls"])],
        expose=True,
    )
    await team.add_agent(
        name="deploy-agent",
        model_capability="deploy",
        skills=[
            Skill(
                "infra.deploy",
                description="deploy services to infrastructure",
                tags=["deploy", "infra"],
            )
        ],
        expose=True,
    )
    return team


async def test_plan_playbook_returns_playbook(team):
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", requires_skill="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    assert isinstance(result, Playbook)


async def test_plan_playbook_step_count(team):
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", requires_skill="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    assert len(result.steps) == 2


async def test_plan_playbook_step_instructions(team):
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", requires_skill="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    assert result.steps[0].instruction == "Rotate the TLS certificate"
    assert result.steps[1].instruction == "Redeploy the service"


async def test_plan_playbook_step_requires_skill(team):
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", requires_skill="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    assert result.steps[0].requires_skill == "cert.rotate"
    assert result.steps[1].requires_skill == "infra.deploy"


async def test_plan_playbook_steps_are_step_instances(team):
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", requires_skill="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    for s in result.steps:
        assert isinstance(s, Step)


async def test_prompt_includes_skill_id(team):
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate")]
    )
    fake = FakeClient(fixed_plan)

    plan_playbook("rotate cert", team, client=fake)

    assert "cert.rotate" in fake.last_prompt


async def test_prompt_includes_second_agent_skill_id(team):
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[PlannedStep(instruction="Deploy", requires_skill="infra.deploy")]
    )
    fake = FakeClient(fixed_plan)

    plan_playbook("deploy service", team, client=fake)

    assert "infra.deploy" in fake.last_prompt


async def test_prompt_includes_goal(team):
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[PlannedStep(instruction="Rotate the TLS certificate", requires_skill="cert.rotate")]
    )
    fake = FakeClient(fixed_plan)

    goal = "rotate cert and redeploy"
    plan_playbook(goal, team, client=fake)

    assert goal in fake.last_prompt
