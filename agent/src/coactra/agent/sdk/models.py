"""Map a litellm-style model id to a pydantic-ai model id (Slice 1).

litellm uses "provider/model"; pydantic-ai uses "provider:model". A bare id with
no provider defaults to the openai provider (pydantic-ai's own default convention).
Slice 2 replaces this with a litellm-backed custom Model so all providers route
through litellm with coactra-ai's thinking-model handling.
"""
from __future__ import annotations


def normalize_model_id(model: str) -> str:
    if ":" in model:
        return model
    if "/" in model:
        provider, _, name = model.partition("/")
        return f"{provider}:{name}"
    return f"openai:{model}"
