"""Compatibility alias for :mod:`coactra.jobs`.

Install ``coactra-jobs`` and prefer ``coactra.jobs`` for new code.
"""
from __future__ import annotations

from importlib import import_module
import sys

_impl = import_module("coactra.jobs")
for _suffix in (
    "_tenant_router",
    "facade",
    "work",
    "work.adapters",
    "work.adapters._optional",
    "work.adapters.a2a",
    "work.adapters.cloudevents",
    "work.adapters.dapr",
    "work.adapters.dbos",
    "work.adapters.fsspec",
    "work.adapters.mcp_tasks",
    "work.adapters.opentelemetry",
    "work.adapters.temporal",
    "work.backends",
    "work.backends.inmemory",
    "work.backends.sql",
    "work.conformance",
    "work.domain",
    "work.domain.artifacts",
    "work.domain.capabilities",
    "work.domain.events",
    "work.domain.models",
    "work.domain.plans",
    "work.domain.scope",
    "work.service",
    "work.store",
    "work.routing",
    "workflow",
    "workflow.adapters",
    "workflow.adapters._external",
    "workflow.adapters._stub",
    "workflow.adapters.prefect",
    "workflow.adapters.temporal",
    "workflow.backends",
    "workflow.conformance",
    "workflow.domain",
    "workflow.domain.models",
    "workflow.domain.scope",
    "workflow.engine",
    "workflow.handlers",
    "workflow.induction",
    "workflow.models",
    "workflow.promotion",
    "workflow.routing",
    "workflow.runtime",
    "workflow.runtime.approval",
    "workflow.runtime.capabilities",
    "workflow.runtime.defaults",
    "workflow.runtime.durable",
    "workflow.runtime.engine",
    "workflow.runtime.handlers",
    "workflow.runtime.tools",
    "workflow.runtime.verification",
    "workflow.scope",
    "workflow.store",
):
    sys.modules[f"{__name__}.{_suffix}"] = import_module(f"coactra.jobs.{_suffix}")

for _name in _impl.__all__:
    globals()[_name] = getattr(_impl, _name)

__all__ = _impl.__all__
__version__ = _impl.__version__
