import pytest

import coactra.team as team


def test_team_module_only_exports_team():
    assert team.__all__ == ["Team"]
    assert team.Team is not None


def test_team_module_rejects_directory_leaks():
    for name in [
        "Organization",
        "OrgStore",
        "OpenFGAAuthorizer",
        "bootstrap_company",
    ]:
        with pytest.raises(AttributeError):
            getattr(team, name)
