"""Back-compat shim — ``SqliteOrgStore`` now lives in ``repository.sqlite_store``."""

from __future__ import annotations

from fleetlib.organization.repository.sqlite_store import SqliteOrgStore

__all__ = ["SqliteOrgStore"]
