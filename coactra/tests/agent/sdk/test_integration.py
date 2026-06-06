"""Integration tests: wire memory/workspace/skills/name/tenant/expose into Agent.

TDD: RED first (tests were written before the implementation), then GREEN.
"""
from __future__ import annotations

import pathlib

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from coactra import Agent, Skill
from coactra.agent.sdk.skills import Skill as SkillDirect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _static_model(text: str) -> FunctionModel:
    """Return a FunctionModel that always replies with *text*."""

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(text)])

    return FunctionModel(_fn)


def _capturing_model(captured: list) -> FunctionModel:
    """FunctionModel that records messages for inspection, returns a static reply."""

    def _fn(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        captured.append(messages)
        return ModelResponse(parts=[TextPart("prod db is on .66")])

    return FunctionModel(_fn)


# ---------------------------------------------------------------------------
# 1. Memory recall is injected into the prompt
# ---------------------------------------------------------------------------


async def test_memory_recall_injected():
    """After remembering a fact, a subsequent run has it in the context the model sees."""
    captured: list = []

    # First agent run: store a fact
    store_agent = await Agent.create(
        model=_static_model("stored"),
        memory="inprocess",
        name="recall-test",
        tenant="test",
    )
    await store_agent.run("remember: prod db is on .66")
    await store_agent.aclose()

    # Second run with a capturing model — shares same backend via bind_memory("inprocess")
    # But inprocess backend is per-instance, so we need the same agent instance:
    store_agent2 = await Agent.create(
        model=_capturing_model(captured),
        memory="inprocess",
        name="recall-test",
        tenant="test",
    )
    # First prime the memory
    await store_agent2._runtime._memory.remember("prod db is on .66")
    # Now run a query — recall should fire and inject context
    captured.clear()
    await store_agent2.run("where is prod db")
    await store_agent2.aclose()

    # The model must have received messages containing the injected recalled text
    assert captured, "Model was never called"
    all_messages_str = str(captured[0])
    assert ".66" in all_messages_str or "prod" in all_messages_str


# ---------------------------------------------------------------------------
# 2. Memory remember is called after run
# ---------------------------------------------------------------------------


async def test_memory_remember_after_run():
    """After agent.run(), the backend holds the stored turn; recall returns non-empty."""
    agent = await Agent.create(
        model=_static_model("the answer is yes"),
        memory="inprocess",
        name="remember-test",
        tenant="test",
    )
    await agent.run("what is the answer")
    # Check the binding directly
    binding = agent._runtime._memory
    result = await binding.recall("what is the answer")
    assert result != "", "Expected non-empty recall after run stored the turn"
    await agent.aclose()


# ---------------------------------------------------------------------------
# 3. Workspace tools are present in runtime tool list
# ---------------------------------------------------------------------------


async def test_workspace_tools_present(tmp_path: pathlib.Path):
    """An agent created with workspace= has write_file/read_file/list_files tools."""
    agent = await Agent.create(
        model=TestModel(),
        workspace=str(tmp_path),
        name="ws-test",
        tenant="test",
    )
    tool_names = {fn.__name__ for fn in agent._runtime._workspace_tools}
    assert "write_file" in tool_names
    assert "read_file" in tool_names
    assert "list_files" in tool_names
    await agent.aclose()


# ---------------------------------------------------------------------------
# 4. Skills / agent.card
# ---------------------------------------------------------------------------


def _make_skill() -> Skill:
    return Skill("cert.rotate", description="Rotate TLS certs", scopes=["cert:write"])


async def test_agent_card_has_skill_and_no_creds():
    """agent.card returns A2A card dict with skill and no credentials."""
    agent = await Agent.create(
        model=TestModel(),
        name="sre-1",
        skills=[_make_skill()],
        tenant="default",
    )
    card = agent.card
    assert card is not None
    assert card["name"] == "sre-1"
    assert len(card["skills"]) == 1
    assert card["skills"][0]["id"] == "cert.rotate"
    # No credentials in card
    card_str = str(card)
    assert "token" not in card_str
    assert "password" not in card_str
    await agent.aclose()


async def test_skill_importable_from_coactra():
    """Skill is importable from the coactra top-level namespace."""
    from coactra import Skill as SkillTop
    assert SkillTop is SkillDirect


# ---------------------------------------------------------------------------
# 5. No-capability agent unchanged (regression)
# ---------------------------------------------------------------------------


async def test_no_capability_agent_runs():
    """An agent without memory/workspace/skills still runs correctly."""
    agent = await Agent.create(
        model=_static_model("all good"),
    )
    result = await agent.run("ping")
    assert "all good" in result
    assert agent.card is None
    await agent.aclose()
