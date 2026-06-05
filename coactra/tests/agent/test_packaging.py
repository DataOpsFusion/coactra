import importlib


def test_agent_imports():
    mod = importlib.import_module("coactra.agent")
    assert mod.__name__ == "coactra.agent"


def test_coactra_is_namespace_package():
    import coactra

    # PEP 420 namespace packages have no __file__ and a virtual __path__.
    assert getattr(coactra, "__file__", None) is None
    assert hasattr(coactra, "__path__")
