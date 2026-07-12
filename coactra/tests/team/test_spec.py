from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from coactra import AgentSpec, Scope, Team
from coactra.agent.skills import Skill


@pytest.mark.asyncio
async def test_team_from_spec_builds_agents_and_routes_skills():
    team = await Team.from_spec(
        model=TestModel(),
        tenant_id="acme",
        namespace="spec",
        agents=[
            AgentSpec("builder", skills=(Skill("python", tags=("implement",)),), expose=True),
            AgentSpec("reviewer", skills=(Skill("python", tags=("review",)),), expose=True),
        ],
    )

    assert team.scope == Scope(tenant_id="acme", namespace="spec")
    assert team.member("builder") is not None
    assert team.match_skill("python", required_tags=["review"]).name == "reviewer"
