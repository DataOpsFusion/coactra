"""Workflow engine backends."""

try:
    from coactra.jobs.workflow.backends.langgraph import LangGraphEngine
except ImportError as exc:  # pragma: no cover - only when langgraph is not installed
    _LANGGRAPH_IMPORT_ERROR = exc

    class LangGraphEngine:
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "LangGraphEngine requires the langgraph dependency"
            ) from _LANGGRAPH_IMPORT_ERROR


try:
    from coactra.jobs.workflow.backends.durable_langgraph import (
        DurableLangGraphEngine,
    )
except ImportError as exc:  # pragma: no cover - only when optional deps are missing
    _DURABLE_LANGGRAPH_IMPORT_ERROR = exc

    class DurableLangGraphEngine:
        def __init__(self, *args, **kwargs) -> None:
            raise ImportError(
                "DurableLangGraphEngine requires the langgraph dependency"
            ) from _DURABLE_LANGGRAPH_IMPORT_ERROR


__all__ = ["LangGraphEngine", "DurableLangGraphEngine"]
