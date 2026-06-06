import importlib
import pathlib


def test_namespace_package_imports():
    mod = importlib.import_module("coactra.ai")
    assert mod.__name__ == "coactra.ai"


def test_no_top_level_init():
    # PEP 420: coactra must NOT have its own __init__.py
    # layout: <repo>/coactra/tests/lib-ai/test_packaging.py -> <repo>/coactra/src/coactra/
    root = pathlib.Path(__file__).resolve().parents[2]
    assert not (root / "src" / "coactra" / "__init__.py").exists()
