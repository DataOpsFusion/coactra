import pytest

from fleetlib.agent import (
    DelegationGrant,
    ExchangedIdentity,
    Hop,
    InProcessExchanger,
    Scope,
    TokenExchanger,
    TokenPassthroughError,
)
from fleetlib.agent.domain.identity import Hop as DomainHop

ACME = Scope(tenant_id="acme")


def test_in_process_exchanger_satisfies_protocol():
    assert isinstance(InProcessExchanger(), TokenExchanger)


def test_grant_carries_subject_and_actor():
    g = DelegationGrant(subject_token="human-tok", actor="agent:platform")
    assert g.subject_token == "human-tok"
    assert g.actor == "agent:platform"


def test_keystone_raw_subject_token_never_appears_downstream():
    # The whole point of RFC 8693 vs passthrough: the human's token MUST NOT travel
    # downstream. The exchanged identity is a fresh credential; the subject token only
    # named WHO is being acted for, never as a bearer credential.
    grant = DelegationGrant(subject_token="SECRET-HUMAN-TOKEN", actor="agent:platform")
    identity = InProcessExchanger().exchange(grant, ACME)

    assert isinstance(identity, ExchangedIdentity)
    assert identity.token != "SECRET-HUMAN-TOKEN"
    assert "SECRET-HUMAN-TOKEN" not in identity.token
    # the subject is recorded as a SUBJECT (who), not re-emitted as a credential
    assert identity.subject == "agent:platform"
    assert "SECRET-HUMAN-TOKEN" not in repr(identity)
    # ...and it appears nowhere in the serialized identity either
    assert "SECRET-HUMAN-TOKEN" not in identity.model_dump_json()


def test_passthrough_attempt_is_rejected():
    ex = InProcessExchanger()
    with pytest.raises(TokenPassthroughError):
        ex.exchange(
            DelegationGrant(subject_token="tok", actor="agent:x", _passthrough=True),
            ACME,
        )


def test_exchanged_identity_is_tenant_scoped():
    identity = InProcessExchanger().exchange(
        DelegationGrant(subject_token="t", actor="agent:x"), ACME
    )
    assert identity.tenant_id == "acme"


# --- the immutable actor-chain (cons linked list) DSA ---------------------------------


def test_multi_hop_flattens_to_the_full_delegation_path():
    # human -> platform -> security : the chain records the full delegation path oldest-first
    ex = InProcessExchanger()
    first = ex.exchange(
        DelegationGrant(subject_token="human-tok", actor="agent:platform"), ACME
    )
    second = ex.exchange_from(first, actor="agent:security", scope=ACME)
    assert second.act_chain == ["agent:platform", "agent:security"]
    assert "human-tok" not in second.token


def test_keystone_chain_is_immutable_prior_identity_unchanged_after_further_hop():
    # Extending a chain allocates a NEW head sharing the tail; the prior identity's chain
    # is structurally untouched. A mutation that appended in place would fail this.
    ex = InProcessExchanger()
    first = ex.exchange(
        DelegationGrant(subject_token="human-tok", actor="agent:platform"), ACME
    )
    assert first.act_chain == ["agent:platform"]
    assert first.chain.depth == 1

    second = ex.exchange_from(first, actor="agent:security", scope=ACME)
    third = ex.exchange_from(second, actor="agent:network", scope=ACME)

    # the older identities did NOT grow
    assert first.act_chain == ["agent:platform"]
    assert first.chain.depth == 1
    assert second.act_chain == ["agent:platform", "agent:security"]
    assert second.chain.depth == 2
    assert third.act_chain == ["agent:platform", "agent:security", "agent:network"]
    assert third.chain.depth == 3

    # structural sharing: third's tail IS second's chain head (cons sharing, not a copy)
    assert third.chain.prev == second.chain
    # frozen cells: a hop cannot be mutated in place
    with pytest.raises(Exception):
        first.chain.subject = "tampered"


def test_hop_extend_returns_new_head_and_leaves_original_intact():
    root = DomainHop(subject="human", actor="agent:platform")
    extended = root.extend(subject="agent:platform", actor="agent:security")
    assert isinstance(extended, Hop)
    assert root.prev is None  # original head untouched
    assert root.actors() == ["agent:platform"]
    assert extended.actors() == ["agent:platform", "agent:security"]
    assert extended.prev == root
