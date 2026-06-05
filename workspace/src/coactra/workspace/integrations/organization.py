"""Compatibility wrapper for the renamed directory integration.

Use coactra.workspace.integrations.directory in new code.
"""

from coactra.workspace.integrations.directory import (
    MemoryAcl,
    ScopeViolation,
    scope_write_action,
    write_action,
)

__all__ = [
    "MemoryAcl",
    "ScopeViolation",
    "scope_write_action",
    "write_action",
]
