import importlib


def test_memory_imports():
    mod = importlib.import_module("fleetlib.memory")
    assert mod is not None


def test_fleetlib_is_namespace_package():
    import fleetlib

    # PEP 420 namespace packages have no __file__ and an empty/virtual __path__ entry list.
    assert getattr(fleetlib, "__file__", None) is None
    assert hasattr(fleetlib, "__path__")
