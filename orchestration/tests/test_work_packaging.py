import importlib


def test_work_imports():
    mod = importlib.import_module("coactra.work")
    assert mod.__version__ == "0.1.0"


def test_coactra_is_namespace_package():
    import coactra

    assert getattr(coactra, "__file__", None) is None
    assert hasattr(coactra, "__path__")
