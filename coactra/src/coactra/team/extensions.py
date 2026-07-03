"""Team extension protocol.

Extensions are host-owned packages that add capabilities to a Team. They can
register agents, model routes, skills, workflows, MCP servers, A2A peers, or
adapter objects without Coactra owning that external system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from coactra.team.facade import Team


@runtime_checkable
class TeamExtension(Protocol):
    """A plugin-like object that installs capabilities into a Team."""

    name: str

    def install(self, team: Team) -> object: ...


__all__ = ["TeamExtension"]
