"""TDD tests for planner — plan_playbook turns a goal + Team into a Playbook.

RED phase: tests written before planner.py exists.

Covers:
1. plan_playbook returns a Playbook with steps mapped from LLM output
2. Prompt sent to LLM includes roster skills (roster-aware planning)
3. Steps carry instruction + needs from PlannedStep schema
4. client is injectable (no network in tests)
"""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from coactra.agent import Agent
from coactra.agent.skills import Skill
from coactra.team import Team
from coactra.workflow.playbook import Playbook, Step

# ---------------------------------------------------------------------------
# Fake client — captures prompt, returns a fixed PlannedPlan instance
# ---------------------------------------------------------------------------


class FakeClient:
    """Injectable fake that captures the prompt and returns a fixed PlannedPlan."""

    def __init__(self, response):
        self._response = response
        self.last_prompt: str = ""

    def structured(self, schema, prompt, **kwargs):  # noqa: ARG002 — schema captured implicitly
        self.last_prompt = prompt
        return self._response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def cert_agent():
    return await Agent.create(
        model=TestModel(),
        name="cert-agent",
        tenant="acme",
        skills=[
            Skill("cert.rotate", description="rotate TLS certificates", tags=["cert", "tls"]),
        ],
        expose=True,
    )


@pytest.fixture
async def deploy_agent():
    return await Agent.create(
        model=TestModel(),
        name="deploy-agent",
        tenant="acme",
        skills=[
            Skill(
                "infra.deploy",
                description="deploy services to infrastructure",
                tags=["deploy", "infra"],
            ),
        ],
        expose=True,
    )


@pytest.fixture
def team(cert_agent, deploy_agent):
    return Team([cert_agent, deploy_agent])


# ---------------------------------------------------------------------------
# 1. plan_playbook returns a Playbook with correctly mapped steps
# ---------------------------------------------------------------------------


async def test_plan_playbook_returns_playbook(team):
    """plan_playbook returns a Playbook instance."""
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", needs="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    assert isinstance(result, Playbook)


async def test_plan_playbook_step_count(team):
    """plan_playbook maps every LLM step to a Playbook Step."""
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", needs="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    assert len(result.steps) == 2


async def test_plan_playbook_step_instructions(team):
    """Each Playbook step carries the instruction from PlannedStep."""
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", needs="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    assert result.steps[0].instruction == "Rotate the TLS certificate"
    assert result.steps[1].instruction == "Redeploy the service"


async def test_plan_playbook_step_needs(team):
    """Each Playbook step carries the needs field from PlannedStep."""
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", needs="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    assert result.steps[0].needs == "cert.rotate"
    assert result.steps[1].needs == "infra.deploy"


async def test_plan_playbook_steps_are_step_instances(team):
    """Steps in the returned Playbook are Step dataclass instances."""
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
            PlannedStep(instruction="Redeploy the service", needs="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    result = plan_playbook("rotate cert and redeploy", team, client=fake)

    for s in result.steps:
        assert isinstance(s, Step)


# ---------------------------------------------------------------------------
# 2. Prompt is roster-aware — includes agent skill IDs from the team
# ---------------------------------------------------------------------------


async def test_prompt_includes_skill_id(team):
    """Prompt sent to the LLM contains the skill IDs from team.roster()."""
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
        ]
    )
    fake = FakeClient(fixed_plan)

    plan_playbook("rotate cert", team, client=fake)

    assert "cert.rotate" in fake.last_prompt, (
        f"Expected 'cert.rotate' in prompt but got:\n{fake.last_prompt}"
    )


async def test_prompt_includes_second_agent_skill_id(team):
    """Prompt includes skill IDs from all team members."""
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Deploy", needs="infra.deploy"),
        ]
    )
    fake = FakeClient(fixed_plan)

    plan_playbook("deploy service", team, client=fake)

    assert "infra.deploy" in fake.last_prompt, (
        f"Expected 'infra.deploy' in prompt but got:\n{fake.last_prompt}"
    )


async def test_prompt_includes_goal(team):
    """Prompt contains the goal string."""
    from coactra.agent.planner import PlannedPlan, PlannedStep, plan_playbook

    fixed_plan = PlannedPlan(
        steps=[
            PlannedStep(instruction="Rotate the TLS certificate", needs="cert.rotate"),
        ]
    )
    fake = FakeClient(fixed_plan)

    goal = "rotate cert and redeploy"
    plan_playbook(goal, team, client=fake)

    assert goal in fake.last_prompt, f"Expected goal in prompt but got:\n{fake.last_prompt}"
