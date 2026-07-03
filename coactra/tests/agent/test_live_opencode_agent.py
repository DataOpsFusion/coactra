"""Live Agent check against Opencode."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from coactra import ModelProfile, ModelResolver, ModelRoute, Policy, Scope, Team

OPENCODE_BASE = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/go/v1")
_KEY_FILES = (Path("/tmp/OC.key"), Path("/tmp/oc.key"))


def _opencode_key() -> str | None:
    for key_file in _KEY_FILES:
        if key_file.exists():
            return key_file.read_text().strip()
    return os.environ.get("OC_KEY")


pytestmark = pytest.mark.live
live = pytest.mark.skipif(
    _opencode_key() is None,
    reason="no opencode key (/tmp/OC.key, /tmp/oc.key, or OC_KEY)",
)


@live
async def test_team_add_agent_with_opencode_provider_runs_live():
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    key = _opencode_key()
    provider = OpenAIProvider(base_url=OPENCODE_BASE, api_key=key)
    model = OpenAIChatModel("deepseek-v4-pro", provider=provider)
    team = Team(
        scope=Scope(tenant_id="acme", namespace="live"),
        policy=Policy.permissive(),
        model_resolver=ModelResolver(
            [ModelRoute(capability="live", profile=ModelProfile(name="live", model=model))]
        ),
    )
    agent = await team.add_agent(
        model_capability="live",
        name="live-agent",
        instructions="Be brief.",
    )
    out = await agent.run("Say hi in three words.")
    assert out and out.strip(), "agent.run() returned empty output"
    print(f"\n[live] Agent(deepseek-v4-pro) -> {out!r}")
