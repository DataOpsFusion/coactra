from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from coactra import Scope, Team
from coactra.agent.skills import Skill
from coactra.team.spec import TeamAgentSpec


@pytest.mark.asyncio
async def test_team_from_spec_builds_agents_and_routes_skills():
    team = await Team.from_spec(
        model=TestModel(),
        tenant_id="acme",
        namespace="spec",
        agents=[
            TeamAgentSpec("builder", skills=(Skill("python", tags=("implement",)),), expose=True),
            TeamAgentSpec("reviewer", skills=(Skill("python", tags=("review",)),), expose=True),
        ],
    )

    assert team.scope == Scope(tenant_id="acme", namespace="spec")
    assert team.member("builder") is not None
    assert team.match_skill("python", required_tags=["review"])._name == "reviewer"
