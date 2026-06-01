import importlib


def test_workflow_imports():
    mod = importlib.import_module("fleetlib.workflow")
    assert mod.__name__ == "fleetlib.workflow"


def test_fleetlib_is_namespace_package():
    import fleetlib

    # PEP 420 namespace packages have no __file__ and a virtual __path__.
    assert getattr(fleetlib, "__file__", None) is None
    assert hasattr(fleetlib, "__path__")
