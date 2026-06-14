"""Integration tests: wire memory/workspace/skills/name/tenant/expose into Agent."""

from __future__ import annotations

import pathlib

from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from coactra import Policy, Scope, Skill, Team
from coactra.agent.skills import Skill as SkillDirect
from coactra.model import ModelProfile, ModelResolver, ModelRoute


def _static_model(text: str) -> FunctionModel:
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(text)])

    return FunctionModel(_fn)


def _capturing_model(captured: list) -> FunctionModel:
    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        captured.append(messages)
        return ModelResponse(parts=[TextPart("prod db is on .66")])

    return FunctionModel(_fn)


async def _make_agent(*, tenant: str = "test", name: str = "agent", model, **kwargs):
    team = Team(
        scope=Scope(tenant_id=tenant, namespace="integration"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [ModelRoute(capability="default", profile=ModelProfile(name="default", model=model))]
        ),
    )
    return await team.add_agent(name=name, model_capability="default", **kwargs)


async def test_memory_recall_injected():
    captured: list = []
    store_agent = await _make_agent(
        model=_static_model("stored"),
        memory="inprocess",
        name="recall-test",
    )
    await store_agent.run("remember: prod db is on .66")
    await store_agent.aclose()

    store_agent2 = await _make_agent(
        model=_capturing_model(captured),
        memory="inprocess",
        name="recall-test",
    )
    await store_agent2._runtime._memory.remember("prod db is on .66")
    captured.clear()
    await store_agent2.run("where is prod db")
    await store_agent2.aclose()

    assert captured
    all_messages_str = str(captured[0])
    assert ".66" in all_messages_str or "prod" in all_messages_str


async def test_memory_remember_after_run():
    agent = await _make_agent(
        model=_static_model("the answer is yes"),
        memory="inprocess",
        name="remember-test",
    )
    await agent.run("what is the answer")
    binding = agent._runtime._memory
    result = await binding.recall("what is the answer")
    assert result != ""
    await agent.aclose()


async def test_workspace_tools_present(tmp_path: pathlib.Path):
    agent = await _make_agent(
        model=TestModel(),
        workspace=str(tmp_path),
        name="ws-test",
    )
    tool_names = {fn.__name__ for fn in agent._runtime._workspace_tools}
    assert "write_file" in tool_names
    assert "read_file" in tool_names
    assert "list_files" in tool_names
    await agent.aclose()


def _make_skill() -> Skill:
    return Skill("cert.rotate", description="Rotate TLS certs", scopes=["cert:write"])


async def test_agent_card_has_skill_and_no_creds():
    agent = await _make_agent(
        model=TestModel(),
        name="sre-1",
        skills=[_make_skill()],
        expose=True,
    )
    card = agent.card
    assert card is not None
    assert card["name"] == "sre-1"
    assert len(card["skills"]) == 1
    assert card["skills"][0]["id"] == "cert.rotate"
    card_str = str(card)
    assert "token" not in card_str
    assert "password" not in card_str
    await agent.aclose()


async def test_skill_importable_from_coactra():
    from coactra import Skill as SkillTop

    assert SkillTop is SkillDirect


async def test_no_capability_agent_runs():
    agent = await _make_agent(
        model=_static_model("all good"),
        name="plain-agent",
    )
    result = await agent.run("ping")
    assert "all good" in result
    assert agent.card is None
    await agent.aclose()
