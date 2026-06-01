"""Workspace data models.

ExecResult        — the typed result of a desk command (exit_code / stdout / stderr).
CapabilityManifest — a PASSIVE list of capability references the agent runtime re-mounts.
                     workspace STORES this so the next session knows what to re-mount; it
                     never mounts anything itself (no mount/connect/activate). That boundary
                     is the charter's: "the agent runtime does MCP mounting (workspace only
                     STORES the capability manifest reference)."
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExecResult(BaseModel):
    """The typed result of running a command on the desk."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class CapabilityManifest(BaseModel):
    """Passive reference list of capabilities the agent runtime should mount. Data only."""

    refs: list[str] = Field(default_factory=list)
