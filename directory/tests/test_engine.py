from sqlmodel import Session, select

from coactra.directory import Tenant, make_engine


def test_write_then_read_in_a_new_session_survives():
    # The StaticPool landmine: a plain sqlite:// in-memory engine gives a fresh DB per
    # connection, so a write in one session vanishes in the next. StaticPool fixes it.
    engine = make_engine()  # defaults to in-memory sqlite://
    with Session(engine) as s:
        s.add(Tenant(tenant_id="acme", name="Acme"))
        s.commit()

    with Session(engine) as s:  # brand-new session / connection
        rows = s.exec(select(Tenant)).all()
    assert [t.tenant_id for t in rows] == ["acme"]


def test_tables_are_created_on_make_engine():
    engine = make_engine()
    with Session(engine) as s:
        # No error => the 'tenant' table exists.
        assert s.exec(select(Tenant)).all() == []
