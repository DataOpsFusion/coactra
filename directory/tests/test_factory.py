"""Factory — make_org_store(config) selects a backend (DI composition root)."""

import pytest

from coactra.directory import OrgStore, SqliteOrgStore, make_org_store
from coactra.directory.errors import MissingExtraError


def test_default_config_is_sqlite_in_memory():
    store = make_org_store()
    assert isinstance(store, SqliteOrgStore)
    assert isinstance(store, OrgStore)


def test_explicit_sqlite_url():
    store = make_org_store("sqlite://")
    assert isinstance(store, SqliteOrgStore)


def test_sqlite_file_url_is_passed_through(tmp_path):
    db = tmp_path / "org.db"
    store = make_org_store(f"sqlite:///{db}")
    assert isinstance(store, SqliteOrgStore)


def test_neo4j_config_routes_to_the_stub_and_raises():
    with pytest.raises(MissingExtraError, match="neo4j"):
        make_org_store("neo4j://localhost:7687")


def test_unknown_backend_raises_value_error():
    with pytest.raises(ValueError, match="unsupported"):
        make_org_store("mysql://localhost")
