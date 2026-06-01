import importlib


def test_workflow_imports():
    mod = importlib.import_module("coactra.workflow")
    assert mod.__name__ == "coactra.workflow"


def test_coactra_is_namespace_package():
    import coactra

    # PEP 420 namespace packages have no __file__ and a virtual __path__.
    assert getattr(coactra, "__file__", None) is None
    assert hasattr(coactra, "__path__")
