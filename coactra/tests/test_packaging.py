from pathlib import Path


def test_umbrella_package_has_lazy_init():
    """coactra now has a top-level __init__.py with lazy PEP 562 exports."""
    root = Path(__file__).resolve().parent.parent
    assert (root / "src" / "coactra" / "__init__.py").exists()


def test_team_extra_is_declared():
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    extras = pyproject["project"]["optional-dependencies"]
    assert "team" in extras
    assert "organization" not in extras
    assert extras["team"] == ["sqlmodel>=0.0.21"]
