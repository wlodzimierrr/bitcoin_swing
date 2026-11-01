"""RBT-005 BTC-222 risk invariants over composed replays, the end-to-end replay and the golden plumbing.

Over every composed replay (the composed champion driving BTC-180): never
average down, stops never widen, and aggregate risk at the stop stays within
the configured ceiling at every bar. The engine refuses none of the champion's
intents. The replays include the end-to-end one: entry, TRAIL, ADD, the natural
TRIMs and a composed EXIT (owner review ruling 5), with mutations that show a
broken management half fails it.

The golden scenarios are plumbing replays only (owner review ruling 5,
2026-11-01). The golden fixture is real BTC history with daily prices only and
no champion value is computed on real prices before the RBT-006 freeze, so the
champion's replay inputs hold nothing for those dates and every golden instant
is the accounted ``STRUCTURALLY_UNEVALUABLE`` missing-input row: the tests show
the engine runs the composed champion over each golden bar sequence without
refusal, and nothing about its management. RBT-007 reports the frozen
champion's decisions on the golden periods next to the scripted ones.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from btc_predictor.backtest.engine import run_backtest
from btc_predictor.portfolio.state_machine import ADD, ENTER, EXIT, STOP_MOVE, TRIM
from btc_predictor.research_backtest import management_composer
from btc_predictor.research_backtest.entry_composer import CAUSE_DECISION_PRICE_BAR_MISSING, OUTCOME_STRUCTURALLY_UNEVALUABLE, EntryComposer
from btc_predictor.research_backtest.management_composer import ManagementComposer
from btc_predictor.risk.exposure import calculate_risk_at_stop
from btc_predictor.tests import test_golden_scenarios as golden
from btc_predictor.tests.rbt004_composer_fixtures import Scenario
from btc_predictor.tests.rbt005_management_fixtures import (
    CONFIG,
    EXIT_AT,
    TRAIL_AT,
    end_to_end_replay,
    end_to_end_run,
    natural_run,
    trail_add_run,
    utc,
)

REPLAYS = {"natural": natural_run, "trail_add": trail_add_run, "end_to_end": end_to_end_run}


@pytest.fixture(scope="module", params=sorted(REPLAYS))
def replay(request):
    return REPLAYS[request.param]()


def _maximum_fraction_nav():
    probe = calculate_risk_at_stop(
        [{"tranche_id": "probe", "quantity": Decimal("1"), "entry_price": Decimal("100")}], stop_price=Decimal("90"), nav=Decimal("1000"), config=CONFIG
    )
    return probe.maximum_fraction_nav


def test_a_composed_replay_never_averages_down(replay):
    lifecycle = replay.result.final_lifecycle
    quantity, average, adds = Decimal("0"), None, 0
    for transition in lifecycle.transitions:
        if not transition.accepted or transition.event not in (ENTER, ADD):
            continue
        if average is not None:
            # Rulebook 32 rule 2, read off the accepted ledger itself
            assert transition.price >= average
            adds += 1
        total = quantity + transition.requested_quantity
        average = ((average or Decimal("0")) * quantity + transition.price * transition.requested_quantity) / total
        quantity = total
    assert adds == (0 if replay is natural_run() else 1)


def test_a_composed_replay_never_widens_a_stop(replay):
    stops = [item.stop_price for item in replay.result.final_lifecycle.transitions if item.accepted and item.stop_price is not None]
    assert stops == sorted(stops) and stops


def test_aggregate_risk_at_stop_stays_within_the_ceiling_at_every_bar(replay):
    ceiling = _maximum_fraction_nav()
    marked = [point.risk_fraction_nav for point in replay.result.equity_curve if point.risk_fraction_nav is not None]
    assert marked and max(marked) <= ceiling


def test_the_engine_refuses_none_of_the_champions_intents(replay):
    assert "BACKTEST_INTENT_REFUSED" not in replay.result.reason_codes
    assert not [event for event in replay.result.events if event.status == "REFUSED"]
    assert replay.champion.unaccounted_causes() == () and replay.champion.entry.unaccounted_causes() == ()


# --- the end-to-end replay (owner review ruling 5) ---------------------------------------------


def _end_to_end_failures(run):
    """What the end-to-end replay must show, as a list of failures (empty when it does)."""

    failures = []
    events = [item.event for item in run.result.final_lifecycle.transitions if item.accepted]
    if events[:3] != [ENTER, STOP_MOVE, ADD]:
        failures.append(f"entry, trail and add expected first: {events[:3]}")
    if TRIM not in events[3:-1]:
        failures.append(f"no composed TRIM before the exit: {events}")
    if events[-1:] != [EXIT]:
        failures.append(f"the position must end on a composed EXIT: {events[-1:]}")
    outcomes = {row.decision_at: row.outcome for row in run.champion.ledger}
    if outcomes.get(TRAIL_AT) != "TRAIL" or outcomes.get(EXIT_AT) != "EXIT":
        failures.append(f"TRAIL and EXIT rows expected: {outcomes.get(TRAIL_AT)}, {outcomes.get(EXIT_AT)}")
    exits = [event for event in run.result.events if event.action == "EXIT" and event.status == "EXECUTED"]
    if [event.source_id for event in exits] != [f"rbt005:BITSTAMP:exit:{EXIT_AT.isoformat()}"]:
        failures.append(f"the composed EXIT must execute once: {[event.source_id for event in exits]}")
    if [row for row in run.champion.ledger if row.decision_at > EXIT_AT]:
        failures.append("a management row after the exit")
    if not [row for row in run.champion.entry.ledger if row.decision_at > EXIT_AT]:
        failures.append("the entry half must decide again once flat")
    if run.champion.unaccounted_causes() or run.champion.entry.unaccounted_causes():
        failures.append("unaccounted causes")
    return failures


def test_the_composed_champion_runs_end_to_end():
    run = end_to_end_run()
    assert _end_to_end_failures(run) == []
    assert "BACKTEST_INTENT_REFUSED" not in run.result.reason_codes
    assert run.champion.ledger[-1].intent["exit_reason"] == "HOLD_SCORE_COLLAPSE"


def test_a_management_half_that_never_acts_fails_the_end_to_end_replay():
    real = management_composer._ManagementRun.run

    def silenced(self):
        decision = real(self)
        return replace(decision, intent=None, pending_add=None)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(management_composer._ManagementRun, "run", silenced)
        run = end_to_end_replay()
    assert _end_to_end_failures(run)


def test_a_management_half_that_breaks_fails_the_end_to_end_replay():
    """The review's mutation: every management decision raises; the golden plumbing still passes it."""

    def broken(self):
        raise AssertionError("every management decision is deliberately broken")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(management_composer._ManagementRun, "run", broken)
        with pytest.raises(AssertionError, match="deliberately broken"):
            end_to_end_replay()


# --- the BTC-224 golden plumbing replays (owner review ruling 5) ----------------------------------


@pytest.fixture(scope="module")
def champion_inputs():
    # replay inputs that hold nothing on any golden date (the golden fixture has no replay inputs)
    return Scenario(start=utc(2021, 6, 1), end=utc(2021, 7, 1)).build()


@pytest.mark.parametrize("scenario_id", golden.SCENARIO_IDS)
def test_each_golden_sequence_replays_through_the_composed_champion_as_plumbing(scenario_id, champion_inputs):
    scenario = golden.scenario_by_id(scenario_id)
    bars = golden.scenario_bars(scenario_id)
    champion = ManagementComposer(EntryComposer(champion_inputs, strategy_config=CONFIG))
    result = run_backtest(
        bars, strategy=champion, strategy_config=CONFIG, symbol=bars[0].symbol,
        starting_nav=Decimal(scenario["starting_nav"]), cost_profile=scenario["cost_profile"],
    )
    assert "BACKTEST_INTENT_REFUSED" not in result.reason_codes and "BACKTEST_COMPLETE" in result.reason_codes
    rows = {row.decision_at: row for row in champion.entry.ledger}
    # one decision instant per golden session close, each the accounted missing-input row
    assert sorted(rows) == [bar.ingested_at for bar in bars]
    assert all(row.outcome == OUTCOME_STRUCTURALLY_UNEVALUABLE and row.reasons == (CAUSE_DECISION_PRICE_BAR_MISSING,) for row in rows.values())
    assert champion.ledger == () and champion.entry.unaccounted_causes() == ()
    # the champion's decisions next to the scripted ones
    report = [
        (decision["on"], decision["action"], rows[next(bar.ingested_at for bar in bars if bar.timestamp.date().isoformat() == decision["on"])].outcome)
        for decision in scenario["plan"]["decisions"]
    ]
    assert [(day, action) for day, action, _ in report] == [(decision["on"], decision["action"]) for decision in scenario["plan"]["decisions"]]
    assert {outcome for _, _, outcome in report} == {OUTCOME_STRUCTURALLY_UNEVALUABLE}
