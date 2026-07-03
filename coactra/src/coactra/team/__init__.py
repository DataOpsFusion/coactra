"""coactra.team - public Team facade and extension seam."""

from coactra.team.extensions import TeamExtension
from coactra.team.facade import Team

__all__ = ["Team", "TeamExtension"]
