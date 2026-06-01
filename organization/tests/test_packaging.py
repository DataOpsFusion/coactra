import importlib


def test_organization_imports():
    mod = importlib.import_module("coactra.organization")
    assert mod is not None


def test_coactra_is_namespace_package():
    import coactra

    # PEP 420 namespace packages have no __file__ and expose a virtual __path__.
    assert getattr(coactra, "__file__", None) is None
    assert hasattr(coactra, "__path__")
