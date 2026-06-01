from pathlib import Path


def test_umbrella_package_preserves_namespace_layout():
    root = Path(__file__).resolve().parent.parent
    assert not (root / "src" / "coactra" / "__init__.py").exists()
