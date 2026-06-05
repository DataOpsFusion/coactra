"""Compatibility import for the local workspace backend."""

from coactra.workspace.backends.local import LocalFilesystemBackend, UnsafeLocalExecError

__all__ = ["LocalFilesystemBackend", "UnsafeLocalExecError"]
