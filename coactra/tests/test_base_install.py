"""Base install imports every capability's pure-Python core.

The base `coactra` install (pydantic only) must be able to import every capability
package's core. Heavy backends stay gated behind their extras.
"""

import importlib
import os
import subprocess
import sys

import pytest

CAPABILITY_ROOTS = [
    "coactra.ai",
    "coactra.memory",
    "coactra.workspace",
    "coactra.workflow",
    "coactra.workflow.ledger",
    "coactra.team",
    "coactra.team.directory",
    "coactra.agent",
    "coactra.scope",
    "coactra.errors",
]


@pytest.mark.parametrize("module", CAPABILITY_ROOTS)
def test_capability_core_imports(module):
    importlib.import_module(module)


def test_base_agent_import_does_not_require_agent_extra():
    root = os.path.dirname(os.path.dirname(__file__))
    code = """
import builtins
orig_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "pydantic_ai" or name.startswith("pydantic_ai."):
        raise ModuleNotFoundError(name)
    return orig_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
import coactra.agent
print("ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env={**os.environ, "PYTHONPATH": os.path.join(root, "src")},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_static_token_import_does_not_require_httpx_extra():
    root = os.path.dirname(os.path.dirname(__file__))
    code = """
import builtins
orig_import = builtins.__import__

def guarded_import(name, *args, **kwargs):
    if name == "httpx" or name.startswith("httpx."):
        raise ModuleNotFoundError(name)
    return orig_import(name, *args, **kwargs)

builtins.__import__ = guarded_import
from coactra import StaticToken
assert StaticToken is not None
print("ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env={**os.environ, "PYTHONPATH": os.path.join(root, "src")},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
