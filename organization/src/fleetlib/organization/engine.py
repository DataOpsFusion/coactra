"""Engine factory.

make_engine() builds a sqlmodel engine and creates all tables. For the in-memory
sqlite:// default it uses StaticPool + check_same_thread=False so the SAME in-memory
database is reused across every session/connection — without StaticPool, each new
connection gets a fresh empty DB and writes appear to vanish. File URLs work too.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

# Importing models registers every table on SQLModel.metadata before create_all().
from fleetlib.organization import models as _models  # noqa: F401


def make_engine(url: str = "sqlite://") -> Engine:
    connect_args = {}
    kwargs: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, connect_args=connect_args, **kwargs)
    SQLModel.metadata.create_all(engine)
    return engine
