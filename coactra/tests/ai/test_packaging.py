import importlib
import pathlib


def test_namespace_package_imports():
    mod = importlib.import_module("coactra.ai")
    assert mod.__name__ == "coactra.ai"


def test_top_level_init_exists():
    # coactra now has a top-level __init__.py with lazy PEP 562 exports.
    root = pathlib.Path(__file__).resolve().parents[2]
    assert (root / "src" / "coactra" / "__init__.py").exists()
