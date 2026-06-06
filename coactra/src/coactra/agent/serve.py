"""Inbound A2A serving — expose an Agent as an A2A-compatible Starlette app.

``serve_agent`` builds a Starlette application that routes inbound A2A
requests to ``agent.run``.  It uses the kept adapters:

- ``build_a2a_app`` — assembles the Starlette app from an agent card, a
  handler callable, and optional verifier.  It internally calls
  ``make_a2a_executor`` so callers do not need to construct the executor
  themselves.

The returned app is a plain Starlette application object.  Callers are
responsible for mounting and running it (e.g. with ``uvicorn``).  This
module never starts a live server.

Public API
----------
- ``serve_agent`` — build a Starlette A2A app for an Agent.
"""
from __future__ import annotations

from typing import Any

__all__ = ["serve_agent"]


def serve_agent(
    agent: Any,
    *,
    verifier: Any | None = None,
) -> Any:
    """Expose *agent* as an inbound A2A Starlette app.

    Builds a handler that routes each ``A2AInboundRequest`` to
    ``agent.run(request.task_text())`` and assembles the full Starlette app
    via ``build_a2a_app``.

    Parameters
    ----------
    agent:
        A ``coactra.agent.Agent`` instance.  It must have a non-``None``
        ``card`` property (i.e. it must be created with ``expose=True`` or
        at least one ``skills`` entry).  Raises ``ValueError`` if the card
        is absent — an agent without a card has no A2A identity to publish.
    verifier:
        Optional ``A2ARequestVerifier``.  When ``None``, the app runs in
        insecure/unauthenticated mode (suitable for local development only).
        Pass a verifier in production to enforce JWT / bearer-token checks.

    Returns
    -------
    starlette.applications.Starlette
        A fully assembled Starlette application ready to be mounted under
        any ASGI server.  No live HTTP server is started.

    Raises
    ------
    ValueError
        If ``agent.card`` is ``None`` (no skills, no expose flag).
    RuntimeError
        If the ``a2a`` / ``starlette`` extras are not installed.
    """
    from coactra.agent.adapters.a2a_server import A2AInboundRequest, build_a2a_app

    card = agent.card
    if card is None:
        raise ValueError(
            f"Agent '{getattr(agent, '_name', agent)!r}' has no A2A card. "
            "Create the agent with expose=True or at least one Skill to enable "
            "A2A serving."
        )

    async def _handler(request: A2AInboundRequest) -> str:
        """Route an inbound A2A task to the agent's run method."""
        return await agent.run(request.task_text())

    return build_a2a_app(
        agent_card=card,
        handler=_handler,
        verifier=verifier,
        allow_unauthenticated=verifier is None,
    )
