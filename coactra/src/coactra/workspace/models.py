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
    timed_out: bool = False
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


class ExecOptions(BaseModel):
    """Safety controls for local command execution.

    ``cwd`` is relative to the scoped desk root. ``env`` is an allowlisted set of
    environment overrides. ``inherit_env`` preserves the host environment by default
    for developer ergonomics; production sandbox adapters should generally set their
    own environment policy.
    """

    timeout_seconds: float = Field(default=30.0, gt=0)
    max_output_bytes: int = Field(default=1_000_000, ge=1)
    cwd: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    inherit_env: bool = True


class CapabilityManifest(BaseModel):
    """Passive reference list of capabilities the agent runtime should mount. Data only."""

    refs: list[str] = Field(default_factory=list)
