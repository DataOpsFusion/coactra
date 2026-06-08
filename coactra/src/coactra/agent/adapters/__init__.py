"""Optional protocol adapters.

Outbound A2A transport and Keycloak token exchange are exported here, not from
the package root. For inbound A2A serving, use the a2a-sdk server APIs directly.
"""

from coactra.agent.adapters.a2a import (
    A2ATransport,
    OfficialA2AClient,
    OfficialA2ATransport,
)
from coactra.agent.adapters.keycloak import (
    AsyncKeycloakExchanger,
    KeycloakExchanger,
    TokenExchangeError,
)

__all__ = [
    "A2ATransport",
    "OfficialA2AClient",
    "OfficialA2ATransport",
    "AsyncKeycloakExchanger",
    "KeycloakExchanger",
    "TokenExchangeError",
]
