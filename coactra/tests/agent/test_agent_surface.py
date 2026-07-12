from __future__ import annotations

from coactra.agent.facade import Agent
from coactra.agent.skills import Skill
from coactra.model import ModelProfile, ModelResolver, ModelRoute


class _NullRuntime:
    async def run(self, prompt, *, run_id, output_type=None, message_history=None):
        raise NotImplementedError

    def stream(
        self, prompt, *, run_id, output_type=None, message_history=None, on_result=None
    ):
        raise NotImplementedError


def test_agent_exposes_name_tenant_and_skills():
    agent = Agent(_NullRuntime(), name="helper", tenant="acme", skills=[Skill("python")])
    assert agent.name == "helper"
    assert agent.tenant == "acme"
    assert [skill.id for skill in agent.skills] == ["python"]
    assert isinstance(agent.skills, tuple)


def test_agent_add_skill_deduplicates_by_id():
    agent = Agent(_NullRuntime(), name="helper")
    agent.add_skill(Skill("python"))
    agent.add_skill(Skill("python"))
    assert len(agent.skills) == 1


def test_model_resolver_exposes_capabilities():
    resolver = ModelResolver(
        [ModelRoute(capability="default", profile=ModelProfile(name="default", model="test"))]
    )
    assert resolver.capabilities == ("default",)


async def test_build_agent_from_spec_with_custom_runtime():
    from coactra import AgentSpec, Scope
    from coactra.agent.facade import build_agent

    spec = AgentSpec(
        name="helper",
        runtime=_NullRuntime(),
        skills="review things",
        scope=Scope(tenant_id="acme", agent_id="helper"),
        expose=True,
    )
    agent = await build_agent(spec)
    assert agent.name == "helper"
    assert agent.tenant == "acme"
    assert agent.skills[0].id == "general"
    assert agent.card is not None
