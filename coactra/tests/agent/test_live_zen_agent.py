"""Live Agent test against opencode zen — env-gated, skips cleanly without a key."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from coactra import Policy, Scope, Team
from coactra.model import ModelProfile, ModelResolver, ModelRoute

ZEN_BASE = "https://opencode.ai/zen/go/v1"
_KEY_FILE = Path("/tmp/oc.key")


def _zen_key() -> str | None:
    if os.environ.get("OC_KEY"):
        return os.environ["OC_KEY"]
    if _KEY_FILE.exists():
        return _KEY_FILE.read_text().strip()
    return None


live = pytest.mark.live(
    pytest.mark.skipif(_zen_key() is None, reason="no opencode zen key (/tmp/oc.key or OC_KEY)")
)


@live
async def test_team_add_agent_with_openai_provider_runs_live():
    key = _zen_key()
    provider = OpenAIProvider(base_url=ZEN_BASE, api_key=key)
    model = OpenAIChatModel("qwen3.6-plus", provider=provider)
    team = Team(
        scope=Scope(tenant_id="acme", namespace="live"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [ModelRoute(capability="live", profile=ModelProfile(name="live", model=model))]
        ),
    )
    agent = await team.add_agent(
        name="live-agent",
        instructions="Be brief.",
    )
    out = await agent.run("Say hi in three words.")
    assert out and out.strip(), "agent.run() returned empty output"
    print(f"\n[live] Agent(qwen3.6-plus) -> {out!r}")
