import pytest

from coactra.directory import SqliteOrgStore


@pytest.fixture
def store() -> SqliteOrgStore:
    # Fresh in-memory store per test (StaticPool keeps it alive across sessions).
    return SqliteOrgStore()
