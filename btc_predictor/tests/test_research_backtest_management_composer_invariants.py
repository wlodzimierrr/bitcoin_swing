"""RBT-005 BTC-222 risk invariants over composed replays, and the BTC-224 golden replays.

Over every composed replay (the composed champion driving BTC-180): never
average down, stops never widen, and aggregate risk at the stop stays within
the configured ceiling at every bar. The engine refuses none of the champion's
intents.

The golden scenarios replay their recorded bar sequences with the composed
champion as the strategy. The golden fixture carries daily prices only: no
hourly replay bars, ETF flows or derivatives, so the champion's replay inputs
hold nothing for those dates and every golden instant is the accounted
``STRUCTURALLY_UNEVALUABLE`` missing-input row. No owner is evaluated on that
real history before the RBT-006 freeze. Its decisions are reported next to the
scripted ones; they are not required to match.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from btc_predictor.backtest.engine import run_backtest
from btc_predictor.portfolio.state_machine import ADD, ENTER
from btc_predictor.research_backtest.entry_composer import CAUSE_DECISION_PRICE_BAR_MISSING, OUTCOME_STRUCTURALLY_UNEVALUABLE, EntryComposer
from btc_predictor.research_backtest.management_composer import ManagementComposer
from btc_predictor.risk.exposure import calculate_risk_at_stop
from btc_predictor.tests import test_golden_scenarios as golden
from btc_predictor.tests.rbt004_composer_fixtures import Scenario
from btc_predictor.tests.rbt005_management_fixtures import CONFIG, natural_run, trail_add_run, utc

REPLAYS = {"natural": natural_run, "trail_add": trail_add_run}


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
    assert adds == (1 if replay is trail_add_run() else 0)


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


# --- the BTC-224 golden replays ----------------------------------------------------------------


@pytest.fixture(scope="module")
def champion_inputs():
    # replay inputs that hold nothing on any golden date (the golden fixture has no replay inputs)
    return Scenario(start=utc(2021, 6, 1), end=utc(2021, 7, 1)).build()


@pytest.mark.parametrize("scenario_id", golden.SCENARIO_IDS)
def test_the_champion_replays_each_golden_sequence_without_engine_refusal(scenario_id, champion_inputs):
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
