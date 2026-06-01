import pytest

from fleetlib.memory import Capability, InProcessBackend, Scope

SCOPE = Scope(tenant_id="acme", namespace="agent:1")


def _seeded():
    be = InProcessBackend()
    be.learn(
        [
            "deployment failed because the port was busy",
            "user prefers dark mode in the editor",
            "backup completed in 12 seconds",
        ],
        SCOPE,
    )
    return be


def test_recall_lexical_token_overlap_ranks_match_first():
    be = _seeded()
    out = be.recall("why did the deployment fail", SCOPE)
    assert out
    assert "deployment failed" in out[0].content


def test_recall_respects_limit():
    be = _seeded()
    out = be.recall("the", SCOPE, limit=1)
    assert len(out) <= 1


def test_recall_rejects_unsupported_requested_capability():
    be = _seeded()
    # Caller asks for VECTOR_EMBEDDING shaping the in-process backend can't provide.
    with pytest.raises(ValueError, match="VECTOR_EMBEDDING"):
        be.recall("deployment", SCOPE, capabilities={Capability.VECTOR_EMBEDDING})


def test_recall_accepts_supported_requested_capability():
    be = _seeded()
    out = be.recall("deployment", SCOPE, capabilities={Capability.LEXICAL_RECALL})
    assert out and "deployment failed" in out[0].content
