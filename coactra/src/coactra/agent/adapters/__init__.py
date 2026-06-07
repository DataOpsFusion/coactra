"""Optional protocol adapters.

Implemented adapters are exported here, not from the package root. Import A2A server
helpers from this package or ``coactra.agent.adapters.a2a_server``.
"""

from coactra.agent.adapters.a2a import (
    A2ATransport,
    OfficialA2AClient,
    OfficialA2ATransport,
)
from coactra.agent.adapters.a2a_server import (
    A2AInboundRequest,
    A2ARequestVerifier,
    build_a2a_app,
    make_a2a_executor,
    parse_a2a_envelope,
    render_task_text,
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
    "A2AInboundRequest",
    "A2ARequestVerifier",
    "build_a2a_app",
    "make_a2a_executor",
    "parse_a2a_envelope",
    "render_task_text",
    "AsyncKeycloakExchanger",
    "KeycloakExchanger",
    "TokenExchangeError",
]
