"""Base install imports every capability's pure-Python core.

The base `coactra` install (pydantic only) must be able to import every capability
package's core. Heavy backends stay gated behind their extras.
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


@pytest.mark.parametrize("module", CAPABILITY_ROOTS)
def test_capability_core_imports(module):
    importlib.import_module(module)
