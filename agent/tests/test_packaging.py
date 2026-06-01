import importlib


def test_agent_imports():
    mod = importlib.import_module("fleetlib.agent")
    assert mod.__name__ == "fleetlib.agent"


def test_fleetlib_is_namespace_package():
    import fleetlib

    # PEP 420 namespace packages have no __file__ and a virtual __path__.
    assert getattr(fleetlib, "__file__", None) is None
    assert hasattr(fleetlib, "__path__")
