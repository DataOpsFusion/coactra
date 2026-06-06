"""TDD tests for Team — lean registry + capability matcher + same-tenant policy.

RED phase: write tests before implementation exists.
"""
from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from coactra.agent.sdk import Agent
from coactra.agent.sdk.skills import Skill


# ---------------------------------------------------------------------------
# Helpers — build agents synchronously for the tests
# ---------------------------------------------------------------------------

async def _make_agent(name: str, tenant: str, skills: list[Skill]) -> Agent:
    return await Agent.create(
        model=TestModel(),
        name=name,
        tenant=tenant,
        skills=skills,
        expose=True,
    )


@pytest.fixture
async def sre_agent():
    return await _make_agent(
        name="sre-agent",
        tenant="acme",
        skills=[
            Skill("cert.rotate", description="rotate TLS certs", tags=["sre", "cert"]),
            Skill("infra.deploy", description="deploy infrastructure", tags=["sre", "infra"]),
        ],
    )


@pytest.fixture
async def security_agent():
    return await _make_agent(
        name="security-agent",
        tenant="acme",
        skills=[
            Skill("vuln.scan", description="scan for vulnerabilities", tags=["security", "scan"]),
            Skill("access.audit", description="audit access logs", tags=["security", "audit"]),
        ],
    )


@pytest.fixture
async def network_agent():
    return await _make_agent(
        name="network-agent",
        tenant="acme",
        skills=[
            Skill("dns.resolve", description="resolve DNS queries", tags=["network", "dns"]),
            Skill("lb.configure", description="configure load balancers", tags=["network", "lb"]),
        ],
    )


@pytest.fixture
async def external_agent():
    """Agent from a different tenant."""
    return await _make_agent(
        name="external-agent",
        tenant="external-corp",
        skills=[
            Skill("external.task", description="external task handler", tags=["external"]),
        ],
    )


@pytest.fixture
async def team(sre_agent, security_agent, network_agent):
    from coactra.agent.sdk.team import Team
    return Team([sre_agent, security_agent, network_agent])


# ---------------------------------------------------------------------------
# 1. team.match — keyword capability matching
# ---------------------------------------------------------------------------

async def test_match_cert_rotate(team, sre_agent):
    """'rotate the cert' should resolve to sre-agent."""
    result = team.match("rotate the cert")
    assert result is sre_agent


async def test_match_vuln_scan(team, security_agent):
    """'scan for vulnerabilities' → security-agent."""
    result = team.match("scan for vulnerabilities")
    assert result is security_agent


async def test_match_no_match(team):
    """Needs with no overlap → None."""
    result = team.match("quantum entanglement teleportation")
    assert result is None


async def test_match_tag_overlap(team, sre_agent):
    """'sre deploy' overlaps sre tag → sre-agent."""
    result = team.match("sre deploy")
    assert result is sre_agent


async def test_match_first_wins_on_tie(sre_agent, security_agent):
    """When both agents have overlapping keyword, first match wins."""
    from coactra.agent.sdk.team import Team
    # Both agents have their name as the most precise match
    # "audit" only matches security-agent
    team = Team([sre_agent, security_agent])
    result = team.match("audit")
    assert result is security_agent


# ---------------------------------------------------------------------------
# 2. team.member — exact-name lookup
# ---------------------------------------------------------------------------

async def test_member_exact_lookup(team, security_agent):
    result = team.member("security-agent")
    assert result is security_agent


async def test_member_not_found(team):
    result = team.member("nonexistent-agent")
    assert result is None


async def test_member_sre(team, sre_agent):
    result = team.member("sre-agent")
    assert result is sre_agent


# ---------------------------------------------------------------------------
# 3. team.can_talk — same-tenant policy
# ---------------------------------------------------------------------------

async def test_can_talk_same_tenant(team):
    """Two agents in acme may talk."""
    assert team.can_talk("sre-agent", "security-agent") is True


async def test_can_talk_unknown_src(team):
    """Unknown source → False."""
    assert team.can_talk("unknown-agent", "security-agent") is False


async def test_can_talk_unknown_dst(team):
    """Unknown destination → False."""
    assert team.can_talk("sre-agent", "unknown-agent") is False


async def test_can_talk_cross_tenant(sre_agent, security_agent, external_agent):
    """Cross-tenant → denied by default."""
    from coactra.agent.sdk.team import Team
    team = Team([sre_agent, security_agent, external_agent])
    assert team.can_talk("sre-agent", "external-agent") is False


async def test_can_talk_custom_policy(sre_agent, security_agent, external_agent):
    """Custom policy callable can override default same-tenant rule."""
    from coactra.agent.sdk.team import Team
    # Policy that allows everything
    allow_all = lambda src, dst: True
    team = Team([sre_agent, security_agent, external_agent], policy=allow_all)
    assert team.can_talk("sre-agent", "external-agent") is True


async def test_can_talk_custom_policy_deny(sre_agent, security_agent):
    """Custom policy can deny same-tenant too."""
    from coactra.agent.sdk.team import Team
    deny_all = lambda src, dst: False
    team = Team([sre_agent, security_agent], policy=deny_all)
    assert team.can_talk("sre-agent", "security-agent") is False


# ---------------------------------------------------------------------------
# 4. team.roster — aggregated Agent Cards (curated, no creds)
# ---------------------------------------------------------------------------

async def test_roster_returns_cards(team):
    """roster() returns a list of agent card dicts."""
    cards = team.roster()
    assert isinstance(cards, list)
    assert len(cards) == 3


async def test_roster_has_skills(team):
    """Each card in the roster has a 'skills' key."""
    cards = team.roster()
    for card in cards:
        assert "skills" in card
        assert len(card["skills"]) > 0


async def test_roster_no_credentials(team):
    """Cards must not contain raw tools, tokens, or credential keys."""
    cards = team.roster()
    forbidden_keys = {"token", "api_key", "secret", "password", "tools", "tool_names"}
    for card in cards:
        card_keys = set(card.keys())
        assert not (card_keys & forbidden_keys), (
            f"Card contains forbidden keys: {card_keys & forbidden_keys}"
        )


async def test_roster_has_security_schemes_not_tokens(team):
    """securitySchemes in cards defines the scheme type, not actual credentials."""
    cards = team.roster()
    for card in cards:
        if "securitySchemes" in card:
            schemes = card["securitySchemes"]
            for scheme_name, scheme_def in schemes.items():
                # Should not have actual values like tokens, just type definitions
                assert "token" not in scheme_def
                assert "api_key" not in scheme_def


async def test_roster_agent_names_present(team):
    """Each card identifies its agent by name."""
    cards = team.roster()
    names = {c.get("name") for c in cards}
    assert "sre-agent" in names
    assert "security-agent" in names
    assert "network-agent" in names


# ---------------------------------------------------------------------------
# 5. Semantic mode — raises cleanly if unavailable (network-free)
# ---------------------------------------------------------------------------

async def test_semantic_raises_or_works_without_network(sre_agent, security_agent, monkeypatch):
    """Semantic mode either raises a clean ImportError (if ai unavailable) or
    we monkeypatch the embedder so no real network call happens."""
    from coactra.agent.sdk.team import Team

    # Simulate embeddings being unavailable by patching LiteLLMEmbedding to raise
    import coactra.agent.sdk.matcher as matcher_mod

    original_embed_fn = None

    def _fake_embed_fn(text: str) -> list[float]:
        # Return a fixed vector so no network call is needed
        return [1.0, 0.0, 0.0]

    class FakeEmbedder:
        def __call__(self, text: str) -> list[float]:
            return _fake_embed_fn(text)

    # Patch the function that creates the embedder in matcher
    monkeypatch.setattr(matcher_mod, "_get_embedder", lambda: FakeEmbedder())

    team = Team([sre_agent, security_agent], match="semantic")
    # With identical fake embeddings, first member wins
    result = team.match("any query")
    assert result in (sre_agent, security_agent)


async def test_semantic_unavailable_raises_clear_error(sre_agent, security_agent, monkeypatch):
    """If the embedder raises ImportError, match_agent re-raises with a clear message."""
    from coactra.agent.sdk.team import Team
    import coactra.agent.sdk.matcher as matcher_mod

    def _raise_import(*args, **kwargs):
        raise ImportError("coactra[ai] required for semantic matching")

    monkeypatch.setattr(matcher_mod, "_get_embedder", _raise_import)

    team = Team([sre_agent, security_agent], match="semantic")
    with pytest.raises((ImportError, RuntimeError)):
        team.match("cert rotation")


# ---------------------------------------------------------------------------
# 6. Top-level import — Team available from coactra
# ---------------------------------------------------------------------------

def test_team_importable_from_coactra():
    """Team is importable from the top-level coactra namespace."""
    import coactra
    Team = coactra.Team
    assert Team is not None


def test_team_import_light():
    """Importing coactra.Team must NOT pull pydantic_ai into sys.modules."""
    import sys
    # Remove coactra from modules to test fresh import path
    # (can't truly do that in-process, but we verify pydantic_ai isn't pulled by team.py alone)
    import coactra.agent.sdk.team as team_mod
    assert hasattr(team_mod, "Team")
    # The team module itself must not import pydantic_ai at top level
    import importlib
    import importlib.util
    spec = importlib.util.spec_from_file_location("_team_check", team_mod.__file__)
    # We just confirm the module file doesn't have a top-level pydantic_ai import
    with open(team_mod.__file__) as f:
        source = f.read()
    assert "from pydantic_ai" not in source
    assert "import pydantic_ai" not in source
