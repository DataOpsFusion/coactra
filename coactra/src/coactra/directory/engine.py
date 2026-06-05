"""Engine factory.

make_engine() builds a sqlmodel engine and creates all tables. For the in-memory
sqlite:// default it uses StaticPool + check_same_thread=False so the SAME in-memory
database is reused across every session/connection — without StaticPool, each new
connection gets a fresh empty DB and writes appear to vanish. File URLs work too.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

# Importing models registers every table on the library-private ``org_metadata``
# (NOT the global SQLModel.metadata) before create_all().
from coactra.directory.models import org_metadata


def make_engine(url: str = "sqlite://") -> Engine:
    connect_args = {}
    kwargs: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, connect_args=connect_args, **kwargs)
    # Create exactly this library's tables — on the private metadata, so a host
    # application's SQLModel tables are neither created here nor collided with.
    org_metadata.create_all(engine)
    return engine
