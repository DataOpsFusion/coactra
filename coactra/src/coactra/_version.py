"""Version helpers for package roots.

Coactra ships as one distribution, so capability roots expose the installed
distribution version instead of maintaining per-package literals.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def distribution_version() -> str:
    try:
        return version("coactra")
    except PackageNotFoundError:  # pragma: no cover - source tree without metadata.
        return "0.0.0"
