import importlib
import pathlib


def test_namespace_package_imports():
    mod = importlib.import_module("fleetlib.ai")
    assert mod.__name__ == "fleetlib.ai"


def test_no_top_level_init():
    # PEP 420: fleetlib must NOT have its own __init__.py
    root = pathlib.Path(__file__).resolve().parent.parent
    assert not (root / "src" / "fleetlib" / "__init__.py").exists()
