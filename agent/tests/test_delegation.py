import pytest

from fleetlib.agent import (
    DelegationGrant,
    ExchangedIdentity,
    InProcessExchanger,
    Scope,
    TokenExchanger,
    TokenPassthroughError,
)

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
    # The subject is recorded as a SUBJECT (who), not re-emitted as a credential.
    assert identity.subject == "agent:platform" or identity.act_chain  # acting party known
    assert "SECRET-HUMAN-TOKEN" not in repr(identity)


def test_passthrough_attempt_is_rejected():
    # If a caller tries to reuse the raw subject token AS the downstream token, refuse.
    ex = InProcessExchanger()
    with pytest.raises(TokenPassthroughError):
        ex.exchange(
            DelegationGrant(subject_token="tok", actor="agent:x", _passthrough=True),
            ACME,
        )


def test_multi_hop_builds_a_nested_actor_chain():
    # human -> platform -> security : the act chain records the full delegation path.
    ex = InProcessExchanger()
    first = ex.exchange(
        DelegationGrant(subject_token="human-tok", actor="agent:platform"), ACME
    )
    second = ex.exchange_from(first, actor="agent:security", scope=ACME)
    assert second.act_chain == ["agent:platform", "agent:security"]
    assert "human-tok" not in second.token


def test_exchanged_identity_is_tenant_scoped():
    identity = InProcessExchanger().exchange(
        DelegationGrant(subject_token="t", actor="agent:x"), ACME
    )
    assert identity.tenant_id == "acme"
