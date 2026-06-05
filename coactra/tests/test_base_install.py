"""Base install imports every capability's pure-Python core; compat shims resolve.

The base `coactra` install (pydantic only) must be able to import every capability
package's core. Heavy backends stay gated behind their extras; the deprecated
namespaces (orchestration/work/workflow/organization) must still resolve to the
canonical jobs/directory packages.
"""

import importlib

import pytest

CAPABILITY_ROOTS = [
    "coactra.ai",
    "coactra.memory",
    "coactra.workspace",
    "coactra.jobs",
    "coactra.jobs.work",
    "coactra.jobs.workflow",
    "coactra.directory",
    "coactra.agent",
    "coactra.scope",
    "coactra.errors",
]

COMPAT_SHIMS = [
    "coactra.orchestration",
    "coactra.work",
    "coactra.workflow",
    "coactra.organization",
]


@pytest.mark.parametrize("module", CAPABILITY_ROOTS)
def test_capability_core_imports(module):
    importlib.import_module(module)


@pytest.mark.parametrize("module", COMPAT_SHIMS)
def test_compat_shim_resolves(module):
    importlib.import_module(module)
