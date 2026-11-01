"""RBT-005 owner composition rulings (2026-11-01).

1. The add is evaluated before the stop moves; the TRAIL is emitted at t and
   the ADD, carrying the requirements evaluated at t, at the first engine
   callback after the raised stop is installed, or it is dropped with a reason.
2. One intent per decision: EXIT > TRIM > TRAIL/ADD; a deferred trail keeps its
   higher low for the next decision.
3. The unmodelled add and reduce rules are recorded, not enforced.

Owner review rulings (2026-11-01): 4. the ADD's projected risk at the stop is
checked again at the callback that emits it; 6(b). a pending ADD whose first
callback is a decision instant is superseded. Review F4: any accepted transition
but the ADD's own trail drops it.

Branches the synthetic market does not reach are shown with named
interventions (a stated owner input or result at a stated instant; the real
owners always run).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from btc_predictor.research_backtest import entry_composer, management_composer
from btc_predictor.portfolio.state_machine import DEFEND, apply_position_event
from btc_predictor.research_backtest.management_composer import (
    DROP_POSITION_CHANGED,
    DROP_POSITION_CLOSED,
    DROP_RISK_EXCEEDED_AT_CALLBACK,
    DROP_SUPERSEDED_BY_DECISION,
    DROP_TRAIL_NOT_APPLIED,
    FOLLOWUP_ADD_DROPPED,
    FOLLOWUP_ADD_EMITTED,
    OUTCOME_EXIT,
    OUTCOME_HOLD,
    OUTCOME_TRAIL,
    OUTCOME_TRIM,
    REASON_ADD_PENDING_TRAIL,
    REASON_ADD_SUPPRESSED_BY_EXIT,
    REASON_ADD_SUPPRESSED_BY_TRIM,
    REASON_TRAIL_DEFERRED_BY_TRIM,
)
from btc_predictor.risk.trailing import apply_trailing_stop
from btc_predictor.tests.rbt005_management_fixtures import (
    CONFIG,
    DAY,
    ENGINE_START,
    HOUR,
    TRAIL_AT,
    Interventions,
    add_score_lifted,
    callback_context,
    decision_price,
    engine_bars,
    higher_low_at,
    managed_run,
    management_market,
    natural_run,
    pending_trail_add,
    resolver_holding,
    trail_add_run,
    utc,
)

TRIM_AT = utc(2024, 4, 6)  # a natural TRIM (flow deterioration) instant
HOLD_AFTER_TRIM = utc(2024, 4, 7)  # the next instant is a natural HOLD


@pytest.fixture(scope="module")
def trail_add():
    return trail_add_run()


def _trail_and_add(inputs):
    def setup(interventions: Interventions) -> None:
        higher_low_at(interventions, inputs, {TRAIL_AT})
        add_score_lifted(interventions, {TRAIL_AT})

    return setup


@pytest.fixture(scope="module")
def dropped():
    """Three runs whose pending ADD is dropped: trail not applied, position closed, superseded."""

    market = management_market(end=utc(2024, 4, 8))
    inputs = market.build()
    runs = {}
    # the trail's eligible bar (TRAIL_AT 00:00) is absent from the engine's bars: the TRAIL expires
    runs["not_applied"] = managed_run(
        market, engine_end=utc(2024, 4, 3, 6), setup=_trail_and_add(inputs),
        bars=lambda built: engine_bars(built, ENGINE_START, utc(2024, 4, 3, 6), drop=(TRAIL_AT,)),
    )

    # the eligible bar trades through the standing stop: the stop executes first
    def crash(built):
        bars = tuple(replace(bar, low=Decimal(1)) if bar.timestamp == TRAIL_AT else bar for bar in built.dataset.price_bars)
        return replace(built, dataset=replace(built.dataset, price_bars=bars))

    runs["closed"] = managed_run(market, engine_end=utc(2024, 4, 3, 6), setup=_trail_and_add(inputs), modify=crash)
    # no engine bar between the TRAIL and the next decision instant
    quiet = tuple(TRAIL_AT + HOUR * hour for hour in range(23))
    runs["superseded"] = managed_run(
        market, engine_end=utc(2024, 4, 3, 6), setup=_trail_and_add(inputs),
        bars=lambda built: engine_bars(built, ENGINE_START, utc(2024, 4, 3, 6), drop=quiet),
    )
    return runs


@pytest.fixture(scope="module")
def deferred():
    """A higher low at a TRIM instant, the same higher low at the next (HOLD) instant."""

    market = management_market(end=utc(2024, 4, 10))
    inputs = market.build()
    level = (decision_price(inputs, TRIM_AT) * Decimal("0.985")).quantize(Decimal("0.01"))

    def setup(interventions: Interventions) -> None:
        higher_low_at(interventions, inputs, {TRIM_AT, HOLD_AFTER_TRIM}, formed=TRIM_AT - DAY, price=level)

    return managed_run(market, engine_end=utc(2024, 4, 8, 6), setup=setup)


# --- ruling 1: the add follows its trail ----------------------------------------------------------


def test_the_trail_is_emitted_at_t_and_the_add_follows_at_the_next_callback(trail_add):
    row = trail_add.rows()[TRAIL_AT]
    assert row.outcome == OUTCOME_TRAIL and row.reasons == ("TRAILING_STOP_ADVANCED", REASON_ADD_PENDING_TRAIL)
    assert row.intent["action"] == "TRAIL" and row.add["outcome"] == "PENDING_TRAIL"
    assert ("evaluate_higher_low_trigger", TRAIL_AT) in trail_add.applied and ("calculate_add_score", TRAIL_AT) in trail_add.applied
    timeline = [
        (event.occurred_at, event.event_type, event.action, event.status)
        for event in trail_add.result.events
        if TRAIL_AT <= event.occurred_at <= TRAIL_AT + 2 * HOUR and event.status != "RESTING"
    ]
    assert timeline == [
        (TRAIL_AT, "INTENT", "TRAIL", "QUEUED"),
        (TRAIL_AT + HOUR, "TRAILING_STOP", "TRAIL", "APPLIED"),
        (TRAIL_AT + HOUR, "INTENT", "ADD", "QUEUED"),
        (TRAIL_AT + 2 * HOUR, "ADD_EXECUTION", "ADD", "EXECUTED"),
    ]
    (followup,) = trail_add.champion.add_followups
    assert followup.decision_at == TRAIL_AT and followup.resolved_at == TRAIL_AT + HOUR
    assert followup.outcome == FOLLOWUP_ADD_EMITTED and followup.reasons == ()
    # the ADD carries exactly the requirements evaluated at t
    assert followup.intent == row.add["intent"] and followup.intent["requirements"]["blocked"] is False
    assert followup.intent["source_id"] == f"rbt005:BITSTAMP:add:{TRAIL_AT.isoformat()}"


def test_the_add_is_evaluated_on_the_lifecycle_before_the_stop_moves(trail_add):
    item = trail_add.captured[TRAIL_AT]
    requirements = trail_add.rows()[TRAIL_AT].add["intent"]["requirements"]["inputs"]
    assert requirements["new_structural_confirmation"] is True and Decimal(requirements["signed_risk_improvement"]) > 0
    # Spec sequencing note: on the lifecycle after the STOP_MOVE, the same higher low
    # is TRAILING_STOP_STRUCTURE_ALREADY_USED and the add could never be confirmed.
    with pytest.MonkeyPatch.context() as patch:
        _confirm(patch, trail_add.inputs, TRAIL_AT)
        before = trail_add.redecide(TRAIL_AT)
        trail = before.intent.trailing_stop
        moved = apply_trailing_stop(item.lifecycle, trail, event_time=TRAIL_AT + HOUR)
        after = management_composer.ManagementComposer(trail_add.champion.entry).decide(
            item.decision, lifecycle=replace(moved, last_event_at=TRAIL_AT), nav=item.nav, armed=item.armed, prior_flow=item.prior_flow
        )
    assert before.pending_add is not None
    assert after.row.trail["reason_codes"] == ["TRAILING_STOP_STRUCTURE_ALREADY_USED"]
    assert after.row.add["new_structural_confirmation"] is False and after.pending_add is None


def test_the_next_decision_needs_a_structure_newer_than_the_add(trail_add):
    rows = trail_add.rows()
    after = rows[TRAIL_AT + DAY]
    assert after.position["tranche_count"] == 2
    assert after.add["new_structural_confirmation"] is False


@pytest.mark.parametrize(
    ("name", "reason", "resolved"),
    [
        ("not_applied", DROP_TRAIL_NOT_APPLIED, TRAIL_AT + 2 * HOUR),
        ("closed", DROP_POSITION_CLOSED, TRAIL_AT + HOUR),
        ("superseded", DROP_SUPERSEDED_BY_DECISION, TRAIL_AT + DAY),
    ],
)
def test_a_pending_add_is_dropped_with_its_reason(dropped, name, reason, resolved):
    run = dropped[name]
    row = run.rows()[TRAIL_AT]
    assert row.outcome == OUTCOME_TRAIL and row.add["outcome"] == "PENDING_TRAIL"
    (followup,) = run.champion.add_followups
    assert (followup.decision_at, followup.resolved_at, followup.outcome, followup.reasons) == (TRAIL_AT, resolved, FOLLOWUP_ADD_DROPPED, (reason,))
    assert followup.intent is None
    assert not run.events(action="ADD")
    assert run.champion.unaccounted_causes() == ()


def test_a_state_change_after_the_trail_drops_the_add():
    """Review F4: an accepted DEFEND at the same quantity and stop is a state change (ruling 1)."""

    pending = pending_trail_add()
    defended = apply_position_event(pending.moved, event=DEFEND, event_time=TRAIL_AT + HOUR)
    assert defended.accepted and defended.state != pending.moved.state
    assert (defended.quantity, defended.stop_price) == (pending.moved.quantity, pending.moved.stop_price)
    champion = resolver_holding(pending)
    assert champion._resolve_pending(callback_context(defended), TRAIL_AT + HOUR) is None
    (followup,) = champion.add_followups
    assert followup.outcome == FOLLOWUP_ADD_DROPPED and followup.reasons == (DROP_POSITION_CHANGED,)
    # control: the same callback with only the trail installed emits the ADD
    control = resolver_holding(pending)
    assert control._resolve_pending(callback_context(pending.moved), TRAIL_AT + HOUR) == pending.decision.pending_add


def test_a_decision_instant_supersedes_an_add_whose_trail_is_installed():
    """Owner review ruling 6(b): the fresh decision decides, even with the ADD's trail applied."""

    pending = pending_trail_add()
    champion = resolver_holding(pending)
    assert champion._resolve_pending(callback_context(pending.moved, TRAIL_AT + DAY), TRAIL_AT + DAY) is None
    (followup,) = champion.add_followups
    assert followup.reasons == (DROP_SUPERSEDED_BY_DECISION,) and followup.risk_recheck is None


def test_the_dropped_trails_engine_record(dropped):
    expired = [event.status for event in dropped["not_applied"].events(event_type="INTENT", action="TRAIL")]
    assert expired == ["QUEUED", "EXPIRED"]
    stopped = [event for event in dropped["closed"].events(event_type="STOP_EXECUTION") if event.status == "EXECUTED"]
    assert [event.occurred_at for event in stopped] == [TRAIL_AT + HOUR]


# --- review ruling 4: the ADD's risk at the stop, again at its callback ---------------------------


def _scaled(bar, factor):
    return replace(bar, open=bar.open * factor, high=bar.high * factor, low=bar.low * factor, close=bar.close * factor)


@pytest.fixture(scope="module")
def moved_prices():
    """The trail-and-add market with a 10% rise during the callback's bar, or at the fill bar's open."""

    market = management_market(end=utc(2024, 4, 4))
    inputs = market.build()
    rise = Decimal("1.10")

    def during_callback_bar(built):
        # the bar the callback serves (TRAIL_AT -> +1h) opens unchanged and closes 10% higher
        bars = tuple(
            replace(bar, high=bar.high * rise, close=bar.close * rise) if bar.timestamp == TRAIL_AT
            else _scaled(bar, rise) if bar.timestamp > TRAIL_AT else bar
            for bar in built.dataset.price_bars
        )
        return replace(built, dataset=replace(built.dataset, price_bars=bars))

    def at_fill_open(built):
        # every bar from the ADD's fill bar on is 10% higher: invisible at the callback
        bars = tuple(_scaled(bar, rise) if bar.timestamp >= TRAIL_AT + HOUR else bar for bar in built.dataset.price_bars)
        return replace(built, dataset=replace(built.dataset, price_bars=bars))

    runs = {}
    for name, modify in (("callback", during_callback_bar), ("fill", at_fill_open)):
        runs[name] = managed_run(market, engine_end=TRAIL_AT + 3 * HOUR, setup=_trail_and_add(inputs), modify=modify)
    return runs


def _maximum_marked_risk(run):
    return max(point.risk_fraction_nav for point in run.result.equity_curve if point.risk_fraction_nav is not None)


def test_the_add_rechecks_its_risk_at_the_callback_that_emits_it(trail_add):
    (followup,) = trail_add.champion.add_followups
    recheck = followup.risk_recheck
    bar = next(bar for bar in trail_add.inputs.dataset.price_bars if bar.ingested_at == TRAIL_AT + HOUR)
    # the bar this callback serves, the installed stop, this callback's NAV
    assert (recheck["bar_timestamp"], recheck["price"]) == (bar.timestamp, bar.close)
    assert recheck["stop_price"] == Decimal(trail_add.rows()[TRAIL_AT].intent["trailing_stop"]["stop_price"])
    assert recheck["within_maximum"] is True and followup.unaccounted == ()
    assert recheck["projected_risk_fraction_nav"] <= CONFIG.risk.max_risk_at_stop_fraction_nav
    assert {item["complete"] for item in recheck["owner_reason_codes"].values()} == {True}
    # the resolver alone, from the same state, records the same re-check
    pending = pending_trail_add()
    champion = resolver_holding(pending)
    assert champion._resolve_pending(callback_context(pending.moved), TRAIL_AT + HOUR) == pending.decision.pending_add
    assert champion.add_followups[0].risk_recheck == recheck


def test_an_add_whose_risk_exceeds_the_ceiling_at_its_callback_is_dropped(moved_prices):
    """Review F1: approved at t, the ADD is dropped when the price has moved by its callback."""

    run = moved_prices["callback"]
    ceiling = CONFIG.risk.max_risk_at_stop_fraction_nav
    assert Decimal(run.rows()[TRAIL_AT].add["projected_risk_fraction_nav"]) <= ceiling
    (followup,) = run.champion.add_followups
    assert followup.outcome == FOLLOWUP_ADD_DROPPED and followup.reasons == (DROP_RISK_EXCEEDED_AT_CALLBACK,)
    assert followup.risk_recheck["within_maximum"] is False and followup.risk_recheck["projected_risk_fraction_nav"] > ceiling
    assert not run.events(action="ADD") and _maximum_marked_risk(run) <= ceiling
    assert run.champion.unaccounted_causes() == ()


def test_a_gap_at_the_fill_bars_open_is_the_recorded_limitation(moved_prices):
    """Owner review ruling 4's residual: the frozen engine fills at the next bar's open, unseen at the callback.

    The re-check passes on the callback's bar, the engine fills 10% higher and
    risk at the stop ends above the ceiling. This pins the recorded limitation;
    it changes only with a fill-time check in a new engine version.
    """

    run = moved_prices["fill"]
    (followup,) = run.champion.add_followups
    assert followup.outcome == FOLLOWUP_ADD_EMITTED and followup.risk_recheck["within_maximum"] is True
    (executed,) = [event for event in run.events(event_type="ADD_EXECUTION") if event.status == "EXECUTED"]
    assert Decimal(executed.evidence["reference_price"]) > followup.risk_recheck["price"] * Decimal("1.09")
    assert _maximum_marked_risk(run) > CONFIG.risk.max_risk_at_stop_fraction_nav


# --- ruling 2: one intent per decision, EXIT > TRIM > TRAIL/ADD -----------------------------------


def _confirm(patch, inputs, instant, *, lift=True):
    """The higher low confirms at ``instant``, and every Add Score component is high."""

    level = (decision_price(inputs, instant) * Decimal("0.985")).quantize(Decimal("0.01"))
    real_trigger = entry_composer.evaluate_higher_low_trigger

    def trigger(*args, **kwargs):
        return replace(real_trigger(*args, **kwargs), triggered=True, higher_low_price=level, higher_low_timestamp=instant - DAY, detected_at=instant)

    patch.setattr(entry_composer, "evaluate_higher_low_trigger", trigger)
    if lift:
        real_score = management_composer.calculate_add_score

        def score(inputs, **kwargs):
            return real_score(replace(inputs, new_structure_score=Decimal("100"), momentum_score=Decimal("100")), **kwargs)

        patch.setattr(management_composer, "calculate_add_score", score)


def test_a_trim_defers_the_trail_and_suppresses_the_add(trail_add):
    natural = natural_run()
    instant = utc(2024, 4, 3)
    assert natural.rows()[instant].outcome == OUTCOME_TRIM
    with pytest.MonkeyPatch.context() as patch:
        _confirm(patch, natural.inputs, instant)
        decision = natural.redecide(instant)
    assert decision.row.outcome == OUTCOME_TRIM and decision.intent.action == "TRIM"
    assert decision.row.trail["advanced"] is True and decision.row.trail["deferred"] == REASON_TRAIL_DEFERRED_BY_TRIM
    assert decision.row.add["outcome"] == "SUPPRESSED" and decision.row.add["reasons"] == [REASON_ADD_SUPPRESSED_BY_TRIM]
    assert decision.pending_add is None


def test_an_exit_overrides_a_trim_and_a_trail(trail_add):
    natural = natural_run()
    instant = utc(2024, 4, 3)
    item = natural.captured[instant]
    bear = replace(item.decision.composition.regime_classification, regime="BEAR")
    with pytest.MonkeyPatch.context() as patch:
        _confirm(patch, natural.inputs, instant)
        decision = natural.redecide(instant, regime_classification=bear)
    assert decision.row.outcome == OUTCOME_EXIT and decision.intent.action == "EXIT"
    assert decision.row.trim["signal"] is True and decision.row.trail["advanced"] is True
    # a bear regime also fails REGIME_SUPPORTIVE_PREDICATE, so this add is blocked rather than suppressed
    assert decision.row.add["outcome"] == "BLOCKED" and decision.pending_add is None
    # with the add otherwise free to go, the exit suppresses it
    item_trail = trail_add.captured[TRAIL_AT]
    with pytest.MonkeyPatch.context() as patch:
        _confirm(patch, trail_add.inputs, TRAIL_AT)
        free = trail_add.redecide(TRAIL_AT, armed=replace(item_trail.armed, entry_regime="BULL"),
                                  regime_classification=replace(item_trail.decision.composition.regime_classification, regime="BULL"))
        assert free.pending_add is not None
        exits = _with_exit(patch, trail_add, TRAIL_AT)
    assert exits.row.outcome == OUTCOME_EXIT and exits.row.add["reasons"][-1] == REASON_ADD_SUPPRESSED_BY_EXIT


def _with_exit(patch, run, instant):
    real = management_composer.exit_rules_for_position

    def manual(**kwargs):
        # the research override is DISCRETIONARY and never asserted in a replay; asserted here only to force an exit
        return real(**{**kwargs, "manual_research_override": True, "manual_override_reason": "RBT-005 priority test"})

    patch.setattr(management_composer, "exit_rules_for_position", manual)
    return run.redecide(instant)


def test_a_deferred_trail_keeps_its_higher_low_for_the_next_decision(deferred):
    rows = deferred.rows()
    trimmed, held = rows[TRIM_AT], rows[HOLD_AFTER_TRIM]
    assert trimmed.outcome == OUTCOME_TRIM and trimmed.trail["deferred"] == REASON_TRAIL_DEFERRED_BY_TRIM
    assert held.outcome == OUTCOME_TRAIL and held.trail["structure"]["structure_id"] == trimmed.trail["structure"]["structure_id"]
    applied = [event for event in deferred.events(event_type="TRAILING_STOP") if event.status == "APPLIED"]
    assert [event.occurred_at for event in applied] == [HOLD_AFTER_TRIM + HOUR]
    assert rows[HOLD_AFTER_TRIM + DAY].position["standing_stop"] == held.trail["stop_price"]


# --- ruling 3: the unmodelled add and reduce rules are recorded, not enforced -------------------------


def test_hold_quality_and_positioning_70_do_not_block_an_add(trail_add):
    """Rulebook 20 'Hold, no add' (60-70) and 7.5 'PositioningScore >= 70 to add' have no owner consumer."""

    item = trail_add.captured[TRAIL_AT]
    real = management_composer.calculate_hold_score

    def hold_65(inputs, **kwargs):
        return real(replace(inputs, trend_score=Decimal("65"), flow_score=Decimal("65"), positioning_score=Decimal("65"),
                            structure_score=Decimal("65"), momentum_persistence_score=Decimal("65")), **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        _confirm(patch, trail_add.inputs, TRAIL_AT)
        patch.setattr(management_composer, "calculate_hold_score", hold_65)
        decision = trail_add.redecide(TRAIL_AT, positioning_score=Decimal("65"))
    assert Decimal("60") <= decision.row.hold["score"] < Decimal("70")
    assert item.decision.composition.positioning_score >= Decimal("70") > Decimal("65")
    assert decision.row.outcome == OUTCOME_TRAIL and decision.pending_add is not None
    assert decision.row.outcome != OUTCOME_HOLD
