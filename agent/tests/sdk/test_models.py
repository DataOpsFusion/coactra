import pytest
from coactra.agent.sdk.models import normalize_model_id


@pytest.mark.parametrize("given,expected", [
    ("anthropic/claude-sonnet-4-6", "anthropic:claude-sonnet-4-6"),
    ("openai/gpt-4o", "openai:gpt-4o"),
    ("anthropic:claude-sonnet-4-6", "anthropic:claude-sonnet-4-6"),  # already pydantic-ai form
    ("gpt-4o", "openai:gpt-4o"),  # bare → default to openai provider
])
def test_normalize_model_id(given, expected):
    assert normalize_model_id(given) == expected
