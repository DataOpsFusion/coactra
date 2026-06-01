"""Keycloak RFC 8693 token-exchange adapter — STUB. Will satisfy TokenExchanger; raises
until the oauth extra. The real impl performs an RFC 8693 grant_type=token-exchange call
(subject_token + actor_token) against the AS; it must NEVER forward the raw subject token
downstream."""

from __future__ import annotations

from coactra.agent.adapters._stub import require_extra


class KeycloakExchanger:
    satisfies = "TokenExchanger"

    def __init__(self, *args, **kwargs) -> None:
        require_extra("oauth")
