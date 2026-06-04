"""Optional adapters for organization persistence and authorization."""

from coactra.organization.adapters.openfga import OpenFGAAuthorizer

__all__ = ["OpenFGAAuthorizer"]
