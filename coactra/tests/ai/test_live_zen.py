"""Live tests against opencode zen — env-gated, skip cleanly without a key.

These exercise the two thinking-model fixes end-to-end against the real provider:
  - structured() must return a typed pydantic object from qwen3.6-plus (JSON mode).
  - ask() must return non-empty text from a thinking model even when the model
    spends its whole budget reasoning (content empty -> reasoning_content fallback).

Run with the key present at /tmp/oc.key (or OC_KEY env var):
    .venv/bin/python -m pytest tests/test_live_zen.py -q -s
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import BaseModel

from coactra.ai.client import Client, ask, structured

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


class Person(BaseModel):
    name: str
    age: int


@live
def test_structured_returns_typed_object_from_qwen():
    key = _zen_key()
    out = structured(
        Person,
        "Extract the person: Ada Lovelace, 36",
        model="openai/qwen3.6-plus",
        api_base=ZEN_BASE,
        api_key=key,
        max_retries=2,
    )
    assert isinstance(out, Person)
    assert out.name and out.age == 36
    print(f"\n[live] structured(qwen3.6-plus) -> {out!r}")


@live
def test_ask_returns_nonempty_from_thinking_model_forced_empty_content():
    """Force the empty-content path: a reasoning-heavy prompt with a small token
    budget so the model spends it all in reasoning_content and returns content=''.
    Without the fallback this returns '' (the original bug)."""
    key = _zen_key()
    out = ask(
        "Think step by step in great detail: what is 17*23? Show all your work.",
        model="openai/deepseek-v4-flash",
        api_base=ZEN_BASE,
        api_key=key,
        max_tokens=80,
    )
    assert out and out.strip(), "ask() returned empty from a thinking model"
    print(f"\n[live] ask(deepseek-v4-flash, forced-empty) -> {out!r}")


@live
def test_client_facade_live():
    key = _zen_key()
    c = Client(model="openai/qwen3.6-plus", api_base=ZEN_BASE, api_key=key)
    out = c.structured(Person, "Extract: Grace Hopper, 85", max_retries=2)
    assert isinstance(out, Person) and out.age == 85
    print(f"\n[live] Client.structured(qwen3.6-plus) -> {out!r}")
