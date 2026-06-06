import importlib
import importlib.metadata


def test_work_imports():
    mod = importlib.import_module("coactra.jobs.work")
    assert mod.__version__ == importlib.metadata.version("coactra")


def test_coactra_is_namespace_package():
    import coactra

    assert getattr(coactra, "__file__", None) is None
    assert hasattr(coactra, "__path__")
