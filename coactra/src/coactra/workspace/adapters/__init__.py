"""Workspace backend adapters.

Provider adapters are explicit opt-ins and are not exported from
``coactra.workspace``. There are no shipped provider adapters today; the only
backend is the reference ``LocalFilesystemBackend`` in ``coactra.workspace``.
Real SDK-backed provider adapters (e.g. Daytona/E2B/OpenHands) land here when
implemented.
"""

__all__: list[str] = []
