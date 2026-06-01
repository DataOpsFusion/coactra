"""Live integration tests against the REAL engines.

These hit external services and need credentials, so they SKIP cleanly when the env
isn't configured (never fail). Run them by installing the extra and setting the env:

    pip install coactra-memory[mem0]      # + OPENAI_API_KEY
    pip install coactra-memory[graphiti]  # + NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
"""

import importlib.util
import os

import pytest

from coactra.memory import Memory, Recollection, Scope, make_backend

SCOPE = Scope(tenant="livetest", agent="pytest")


def _installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


_mem0_ready = bool(os.getenv("OPENAI_API_KEY")) and _installed("mem0")
_graphiti_ready = bool(os.getenv("NEO4J_URI")) and _installed("graphiti_core")


@pytest.mark.skipif(not _mem0_ready, reason="mem0 extra + OPENAI_API_KEY not configured")
async def test_live_mem0_remember_recall():
    mem = Memory(backend=make_backend("mem0"))
    await mem.remember(
        [{"role": "user", "content": "We decided to deploy with blue-green releases."}],
        SCOPE,
    )
    hits = await mem.recall("how do we deploy?", SCOPE, k=5)
    assert all(isinstance(h, Recollection) for h in hits)


@pytest.mark.skipif(
    not _graphiti_ready, reason="graphiti extra + NEO4J_URI not configured"
)
async def test_live_graphiti_remember_recall():
    mem = Memory(
        backend=make_backend(
            "graphiti",
            uri=os.environ["NEO4J_URI"],
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", ""),
        )
    )
    await mem.remember(["Service A depends on Service B."], SCOPE)
    hits = await mem.recall("what depends on Service B?", SCOPE, k=5)
    assert all(isinstance(h, Recollection) for h in hits)
