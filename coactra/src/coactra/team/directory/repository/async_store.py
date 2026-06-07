"""Async Postgres directory-store facade.

SQLModel's repository remains the single tenant-checked implementation. Database calls
run in worker threads so async fleet services do not block their event loop. PostgreSQL
provides the shared multi-process persistence; install ``coactra[postgres]``.
"""
from __future__ import annotations

import asyncio
from functools import partial
from typing import Any, Protocol, runtime_checkable

from coactra.team.directory.engine import make_engine
from coactra.team.directory.repository.sqlite_store import SqliteOrgStore
from coactra.team.directory.repository.store import (
    ORG_STORE_METHODS,
    Directory,
    OrgStore,
)


@runtime_checkable
class AsyncOrgStore(Protocol):
    async def add_tenant(self, tenant): ...
    async def add_member(self, tenant_id: str, member): ...
    async def add_seat(self, tenant_id: str, seat): ...
    async def directory(self, tenant_id: str) -> Directory: ...
    async def owner_of(self, tenant_id: str, resource_domain: str): ...
    async def escalate(self, tenant_id: str, seat_id: int): ...


class AsyncPostgresOrgStore:
    """Async facade over the tenant-checked SQL repository using a Postgres engine."""

    def __init__(self, config: str | None = None, *, store: OrgStore | None = None) -> None:
        if store is None:
            if config is None or not config.startswith("postgresql"):
                raise ValueError("AsyncPostgresOrgStore requires a postgresql:// config URL")
            if config.startswith("postgresql://"):
                config = config.replace("postgresql://", "postgresql+psycopg://", 1)
            store = SqliteOrgStore(engine=make_engine(config))
        self._store = store

    def __getattr__(self, name: str):
        # Catch-all for non-Protocol extras (e.g. resolve_decider) and any non-callable
        # attribute. The Protocol surface itself is bound as real async methods by the
        # loop below, so isinstance(x, AsyncOrgStore) holds without faking it here.
        method = getattr(self._store, name)
        if not callable(method):
            return method

        async def call(*args: Any, **kwargs: Any):
            return await asyncio.to_thread(partial(method, *args, **kwargs))

        return call


def _async_forward(name: str):
    async def call(self, *args: Any, **kwargs: Any):
        method = getattr(self._store, name)
        return await asyncio.to_thread(partial(method, *args, **kwargs))
    call.__name__ = name
    return call


# Bind the whole directory SPI (derived from the Protocol — never hand-synced) as real
# async methods so the facade satisfies the async store contract structurally.
for _name in ORG_STORE_METHODS:
    setattr(AsyncPostgresOrgStore, _name, _async_forward(_name))
