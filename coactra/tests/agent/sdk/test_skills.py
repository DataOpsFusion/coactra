"""Tests for coactra.agent.sdk.skills — Structured skills + A2A Agent Card builder.

TDD order: RED (import fails), then GREEN after skills.py is written.
"""
from __future__ import annotations

from coactra.agent.sdk.skills import Skill, build_agent_card, normalize_skills


# ---------------------------------------------------------------------------
# 1. normalize_skills — string shorthand
# ---------------------------------------------------------------------------

def test_normalize_skills_from_string() -> None:
    """A plain string becomes a single Skill with id='general'."""
    result = normalize_skills("rotate certs")
    assert len(result) == 1
    skill = result[0]
    assert skill.id == "general"
    assert skill.description == "rotate certs"


# ---------------------------------------------------------------------------
# 2. normalize_skills — list of Skill + dict; tags/scopes preserved as tuples
# ---------------------------------------------------------------------------

def test_normalize_skills_from_list() -> None:
    """List of Skill and dict objects normalises to 2 Skills with tuple tags/scopes."""
    raw: list = [
        Skill("cert.rotate", description="d", tags=["sre"], scopes=["cert:write"]),
        {"id": "deploy"},
    ]
    result = normalize_skills(raw)
    assert len(result) == 2

    first = result[0]
    assert first.id == "cert.rotate"
    assert first.description == "d"
    assert first.tags == ("sre",)
    assert first.scopes == ("cert:write",)
    # Must be actual tuples (hashable / immutable)
    assert isinstance(first.tags, tuple)
    assert isinstance(first.scopes, tuple)

    second = result[1]
    assert second.id == "deploy"
    assert second.tags == ()
    assert second.scopes == ()


# ---------------------------------------------------------------------------
# 3. build_agent_card — A2A shape, curated only, NO credentials/tokens/tools
# ---------------------------------------------------------------------------

def test_build_agent_card_shape_and_security() -> None:
    """Agent Card contains curated skill metadata; has no creds, no raw tool schema."""
    card = build_agent_card(
        "sre-1",
        [Skill("cert.rotate", description="Rotate TLS", tags=["sre"], scopes=["cert:write"])],
    )

    # Top-level fields
    assert card["name"] == "sre-1"
    assert "skills" in card

    # Curated skill entry
    skills = card["skills"]
    assert len(skills) == 1
    entry = skills[0]
    assert entry["id"] == "cert.rotate"
    assert entry["description"] == "Rotate TLS"
    assert "sre" in entry["tags"]
    assert "cert:write" in entry.get("scopes", [])

    # Security schemes present (A2A requirement)
    assert "securitySchemes" in card

    # -----------------------------------------------------------------------
    # Security invariants: NO credentials, NO raw tool schema
    # -----------------------------------------------------------------------
    # Serialise the entire card as a flat string for substring checks
    card_str = str(card)

    # No raw tool argument schemas
    assert "tools" not in card, "Agent Card must not expose a raw tool list"

    # No credential-like keys or values
    assert "Authorization" not in card_str, "No auth header in card"
    assert "client_secret" not in card_str, "No client_secret in card"
    assert "client_id" not in card_str, "No client_id in card"
    assert "password" not in card_str, "No password in card"
    assert "token" not in card_str, "No token value/header in card"
    assert "api_key" not in card_str.lower() and "apikey" not in card_str.lower()
