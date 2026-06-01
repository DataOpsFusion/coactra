import importlib


def test_organization_imports():
    mod = importlib.import_module("fleetlib.organization")
    assert mod is not None


def test_fleetlib_is_namespace_package():
    import fleetlib

    # PEP 420 namespace packages have no __file__ and expose a virtual __path__.
    assert getattr(fleetlib, "__file__", None) is None
    assert hasattr(fleetlib, "__path__")
