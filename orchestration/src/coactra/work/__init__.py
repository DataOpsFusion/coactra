"""Compatibility alias for :mod:`coactra.orchestration.work`.

Install ``coactra-orchestration`` and prefer the canonical namespace for new code.
"""
from __future__ import annotations

from importlib import import_module
import sys

_impl = import_module("coactra.orchestration.work")
for _suffix in (
    "adapters",
    "adapters._optional",
    "adapters.a2a",
    "adapters.cloudevents",
    "adapters.dapr",
    "adapters.dbos",
    "adapters.fsspec",
    "adapters.mcp_tasks",
    "adapters.opentelemetry",
    "adapters.temporal",
    "backends",
    "backends.inmemory",
    "conformance",
    "domain",
    "domain.artifacts",
    "domain.capabilities",
    "domain.events",
    "domain.models",
    "domain.plans",
    "domain.scope",
    "service",
    "store",
    "routing",
):
    sys.modules[f"{__name__}.{_suffix}"] = import_module(
        f"coactra.orchestration.work.{_suffix}"
    )

for _name in _impl.__all__:
    globals()[_name] = getattr(_impl, _name)

__all__ = _impl.__all__
__version__ = _impl.__version__
