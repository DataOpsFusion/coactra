from coactra.directory import Seat, Tenant


def _chain(store):
    # platform -> manager -> director  (junior to senior)
    store.add_tenant(Tenant(tenant_id="acme"))
    platform = store.add_seat("acme", Seat(tenant_id="acme", role="platform"))
    manager = store.add_seat("acme", Seat(tenant_id="acme", role="manager"))
    director = store.add_seat("acme", Seat(tenant_id="acme", role="director"))
    store.reports_to("acme", platform.id, manager.id)
    store.reports_to("acme", manager.id, director.id)
    return platform, manager, director


def test_escalate_returns_one_tier_up(store):
    platform, manager, _ = _chain(store)
    nxt = store.escalate("acme", platform.id)
    assert nxt.id == manager.id  # returns a Seat, runs nothing


def test_escalate_top_of_chain_returns_none(store):
    _, _, director = _chain(store)
    assert store.escalate("acme", director.id) is None


def test_explicit_route_overrides_reporting_chain(store):
    platform, manager, director = _chain(store)
    # An explicit EscalationRoute from platform jumps straight to director.
    store.set_escalation_route("acme", from_seat_id=platform.id, to_seat_id=director.id)
    assert store.escalate("acme", platform.id).id == director.id


def test_resolve_decider_walks_to_top(store):
    platform, _, director = _chain(store)
    decider = store.resolve_decider("acme", platform.id)
    assert decider.id == director.id  # top of the chain; still just a lookup


def test_escalate_is_pure_lookup_no_side_effects(store):
    platform, manager, _ = _chain(store)
    before = len(store.members("acme"))
    store.escalate("acme", platform.id)
    # No work order, no mutation — member count is unchanged and nothing was created.
    assert len(store.members("acme")) == before
