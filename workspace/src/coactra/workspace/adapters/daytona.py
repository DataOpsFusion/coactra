"""Daytona adapter stub.

Maturity: stub. This class marks the intended WorkspaceBackend seam but does not yet wrap
the Daytona SDK.
"""

from __future__ import annotations

from coactra.workspace.adapters._stub import require_extra


class DaytonaBackend:
    maturity = "stub"
    satisfies = "WorkspaceBackend"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("daytona")
