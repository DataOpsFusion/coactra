"""Optional adapters for directory persistence and authorization."""

from coactra.team.directory.adapters.openfga import OpenFGAAuthorizer

__all__ = ["OpenFGAAuthorizer"]
