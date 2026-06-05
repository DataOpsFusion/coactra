"""Deprecated compatibility import — ``SqliteOrgStore`` now lives in ``repository.sqlite_store``."""

from __future__ import annotations

from coactra.directory.repository.sqlite_store import SqliteOrgStore

__all__ = ["SqliteOrgStore"]
