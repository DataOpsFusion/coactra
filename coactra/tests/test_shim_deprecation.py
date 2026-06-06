"""Compat shim packages emit DeprecationWarning on first import."""

import importlib

import pytest


def test_orchestration_shim_emits_deprecation_warning():
    importlib.invalidate_caches()
    # Re-import after evicting cached module so the warning fires in this test.
    import sys

    sys.modules.pop("coactra.orchestration", None)
    with pytest.warns(DeprecationWarning, match="coactra.orchestration is deprecated"):
        importlib.import_module("coactra.orchestration")
