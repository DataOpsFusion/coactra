"""E2B adapter stub.

Maturity: stub. This class marks the intended WorkspaceBackend seam but does not yet wrap
the E2B SDK.
"""

from __future__ import annotations

from coactra.workspace.adapters._stub import require_extra


class E2BBackend:
    maturity = "stub"
    satisfies = "WorkspaceBackend"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("e2b")
