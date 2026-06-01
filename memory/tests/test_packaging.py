import importlib


def test_memory_imports():
    mod = importlib.import_module("fleetlib.memory")
    assert mod is not None
    assert mod.__version__ == "0.2.0"


def test_fleetlib_is_namespace_package():
    import fleetlib

    # PEP 420 namespace packages have no __file__ and a virtual __path__.
    assert getattr(fleetlib, "__file__", None) is None
    assert hasattr(fleetlib, "__path__")
