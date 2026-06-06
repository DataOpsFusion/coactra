import importlib
import importlib.metadata


def test_memory_imports():
    mod = importlib.import_module("coactra.memory")
    assert mod is not None
    assert mod.__version__ == importlib.metadata.version("coactra")


def test_coactra_is_namespace_package():
    import coactra

    # PEP 420 namespace packages have no __file__ and a virtual __path__.
    assert getattr(coactra, "__file__", None) is None
    assert hasattr(coactra, "__path__")
