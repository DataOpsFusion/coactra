"""Agent error hierarchy."""

from __future__ import annotations

from coactra.errors import ExecutionError


class AgentError(ExecutionError):
    """Base class for agent runtime and adapter errors."""
