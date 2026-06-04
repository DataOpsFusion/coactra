"""Experimental workspace backend adapters.

These names are intentionally not exported from ``coactra.workspace``. Provider adapters
remain explicit opt-ins, and the current Daytona/E2B/OpenHands classes are stubs until real
SDK-backed implementations land.
"""

from coactra.workspace.adapters._stub import MissingExtraError
from coactra.workspace.adapters.daytona import DaytonaBackend
from coactra.workspace.adapters.e2b import E2BBackend
from coactra.workspace.adapters.openhands import OpenHandsBackend

ADAPTER_MATURITY = {
    "DaytonaBackend": "stub",
    "E2BBackend": "stub",
    "OpenHandsBackend": "stub",
}

__all__ = [
    "ADAPTER_MATURITY",
    "DaytonaBackend",
    "E2BBackend",
    "MissingExtraError",
    "OpenHandsBackend",
]
