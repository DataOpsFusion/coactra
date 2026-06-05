"""Shared error for optional-extra workflow engine adapters.

``MissingExtraError`` is raised by the real Prefect/Temporal adapters when their
optional runtime dependency (``coactra-jobs[prefect]`` / ``[temporal]``) is not
installed and no client/runner was injected.
"""

from __future__ import annotations

# Re-export the canonical MissingExtraError; kept importable from this path.
from coactra.errors import MissingExtraError

__all__ = ["MissingExtraError"]
