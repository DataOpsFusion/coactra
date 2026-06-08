"""Live Agent test against opencode zen — env-gated, skips cleanly without a key.

Run with the key present at /tmp/oc.key (or OC_KEY env var):
    .venv/bin/python -m pytest tests/agent/test_live_zen_agent.py -q -s
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from coactra.agent.facade import Agent

ZEN_BASE = "https://opencode.ai/zen/go/v1"
_KEY_FILE = Path("/tmp/oc.key")


def _zen_key() -> str | None:
    if os.environ.get("OC_KEY"):
        return os.environ["OC_KEY"]
    if _KEY_FILE.exists():
        return _KEY_FILE.read_text().strip()
    return None


live = pytest.mark.live(
    pytest.mark.skipif(
        _zen_key() is None, reason="no opencode zen key (/tmp/oc.key or OC_KEY)"
    )
)


@live
async def test_agent_create_with_openai_provider_runs_live():
    """Agent.create() accepts a pydantic-ai Model instance and a real call succeeds."""
    key = _zen_key()
    provider = OpenAIProvider(base_url=ZEN_BASE, api_key=key)
    model = OpenAIChatModel("qwen3.6-plus", provider=provider)
    agent = await Agent.create(
        model=model,
        instructions="Be brief.",
    )
    out = await agent.run("Say hi in three words.")
    assert out and out.strip(), "agent.run() returned empty output"
    print(f"\n[live] Agent(qwen3.6-plus) -> {out!r}")
