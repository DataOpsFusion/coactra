"""Compatibility alias for :mod:`coactra.orchestration.workflow`.

Install ``coactra-orchestration`` and prefer the canonical namespace for new code.
"""
from __future__ import annotations

from importlib import import_module
import sys

_impl = import_module("coactra.orchestration.workflow")
for _suffix in (
    "adapters",
    "adapters._stub",
    "adapters.prefect",
    "adapters.temporal",
    "backends",
    "domain",
    "domain.models",
    "domain.scope",
    "engine",
    "handlers",
    "induction",
    "models",
    "promotion",
    "runtime",
    "runtime.engine",
    "runtime.durable",
    "runtime.defaults",
    "runtime.approval",
    "runtime.handlers",
    "scope",
    "store",
    "adapters._external",
    "conformance",
    "routing",
):
    sys.modules[f"{__name__}.{_suffix}"] = import_module(
        f"coactra.orchestration.workflow.{_suffix}"
    )

for _name in _impl.__all__:
    globals()[_name] = getattr(_impl, _name)

__all__ = _impl.__all__
__version__ = _impl.__version__
