"""OpenHands adapter stub.

Maturity: stub. This class marks the intended WorkspaceBackend seam but does not yet wrap
OpenHands.
"""

from __future__ import annotations

from coactra.workspace.adapters._stub import require_extra


class OpenHandsBackend:
    maturity = "stub"
    satisfies = "WorkspaceBackend"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("openhands")
