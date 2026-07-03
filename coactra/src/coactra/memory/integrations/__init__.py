"""Optional adapters that bind coactra.memory to sibling Coactra packages."""

from __future__ import annotations

from typing import Any

__all__ = [
    "GraphitiAIClient",
    "make_graphiti_ai_client",
    "make_graphiti_ai_clients",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from coactra.memory.integrations.graphiti_ai import (
            GraphitiAIClient,
            make_graphiti_ai_client,
            make_graphiti_ai_clients,
        )

        exports = {
            "GraphitiAIClient": GraphitiAIClient,
            "make_graphiti_ai_client": make_graphiti_ai_client,
            "make_graphiti_ai_clients": make_graphiti_ai_clients,
        }
        return exports[name]
    raise AttributeError(name)
