"""Compatibility alias for :mod:`coactra.directory`.

Install ``coactra-directory`` and prefer ``coactra.directory`` for new code.
"""
from __future__ import annotations

from importlib import import_module
import sys

_impl = import_module("coactra.directory")
for _suffix in (
    "adapters",
    "adapters.neo4j",
    "adapters.openfga",
    "authorization",
    "company",
    "domain",
    "domain.directory",
    "domain.member",
    "domain.organization",
    "domain.permission",
    "domain.seat",
    "engine",
    "errors",
    "factory",
    "models",
    "repository",
    "repository.async_store",
    "repository.neo4j_store",
    "repository.routing",
    "repository.sqlite_store",
    "repository.store",
    "service",
    "sqlite_store",
    "store",
):
    sys.modules[f"{__name__}.{_suffix}"] = import_module(f"coactra.directory.{_suffix}")

for _name in _impl.__all__:
    globals()[_name] = getattr(_impl, _name)

__all__ = _impl.__all__
__version__ = _impl.__version__
