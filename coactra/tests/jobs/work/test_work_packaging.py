import importlib
import importlib.metadata


def test_work_imports():
    mod = importlib.import_module("coactra.jobs.work")
    assert mod.__version__ == importlib.metadata.version("coactra")


def test_coactra_is_regular_package_with_lazy_init():
    import coactra

    # coactra now has a top-level __init__.py with lazy PEP 562 exports.
    assert coactra.__file__ is not None
    assert hasattr(coactra, "__path__")
