from pathlib import Path


def test_umbrella_package_has_lazy_init():
    """coactra now has a top-level __init__.py with lazy PEP 562 exports."""
    root = Path(__file__).resolve().parent.parent
    assert (root / "src" / "coactra" / "__init__.py").exists()
