"""Workspace backend primitives and defaults."""

from coactra.workspace.backends.base import WorkspaceBackend
from coactra.workspace.backends.local import LocalFilesystemBackend, UnsafeLocalExecError

__all__ = ["WorkspaceBackend", "LocalFilesystemBackend", "UnsafeLocalExecError"]
