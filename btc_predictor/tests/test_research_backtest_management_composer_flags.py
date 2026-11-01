"""RBT-005 Rulebook 24 NO ADDING (policy V7 section 7) and the DATA_QUALITY_FAIL add gate.

No ADD intent is issued while STRESS, CROWDING or EUPHORIA is active; each
suppression records ``RULEBOOK_24_NO_ADDING_ENFORCED``. The lifecycle-state
(``DEFEND``) mapping is not chosen. A flag whose state is unknown also blocks
the add (fail closed) and records ``RULEBOOK_24_FLAG_STATE_UNKNOWN``.

The baseline is the trail-and-add instant, where every add requirement passes
and the ADD is left pending on its TRAIL; each case replaces one shared owner
result in the entry composition (a named intervention).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from btc_predictor.research_backtest import entry_composer
from btc_predictor.research_backtest.management_composer import (
    OUTCOME_TRAIL,
    OUTCOME_TRIM,
    REASON_ADD_DATA_QUALITY_GATE,
    REASON_RULEBOOK_24_FLAG_UNKNOWN,
    REASON_RULEBOOK_24_NO_ADDING,
)
from btc_predictor.signals.data_quality import DataQualityFailure
from btc_predictor.tests.rbt005_management_fixtures import (
    TRAIL_AT,
    Interventions,
    add_score_lifted,
    higher_low_at,
    managed_run,
    management_market,
    trail_add_interventions,
    trail_add_run,
    utc,
)

STRESS_VALUES = {
    "volatility_percentile": Decimal("99"),
    "liquidation_percentile": Decimal("99"),
    "downside_return": Decimal("-0.2"),
    "funding_zscore": Decimal("-3"),
    "basis_zscore": Decimal("-3"),
}


@pytest.fixture(scope="module")
def trail_add():
    return trail_add_run()


@pytest.fixture(scope="module")
def composition(trail_add):
    return trail_add.captured[TRAIL_AT].decision.composition


def redecide(run, **changes):
    """TRAIL_AT composed again under the run's own interventions, with ``changes`` to the composition."""

    with trail_add_interventions(run.inputs):
        return run.redecide(TRAIL_AT, **changes)


def test_the_baseline_add_goes_ahead(trail_add):
    decision = redecide(trail_add)
    assert decision.row.outcome == OUTCOME_TRAIL and decision.pending_add is not None
    assert decision.row.add["rulebook_24"] == {"stress": False, "crowding": False, "euphoria": False}


def test_stress_blocks_the_add(trail_add):
    decision = redecide(trail_add, stress_mapped=True)
    assert decision.row.add["rulebook_24"]["stress"] is True
    assert decision.row.add["outcome"] == "BLOCKED" and decision.row.add["reasons"] == [REASON_RULEBOOK_24_NO_ADDING]
    # the trail still goes; no ADD is left pending
    assert decision.row.outcome == OUTCOME_TRAIL and decision.pending_add is None


def test_crowding_blocks_the_add(trail_add, composition):
    crowded = replace(composition.crowding, flagged=True, complete=True)
    decision = redecide(trail_add, crowding=crowded)
    assert decision.row.add["rulebook_24"]["crowding"] is True
    assert REASON_RULEBOOK_24_NO_ADDING in decision.row.add["reasons"]
    # BTC-154's own requirement 6 blocks it too, and CROWDING is also a trim trigger
    assert "ADD_REQUIREMENTS_POSITIONING_UNHEALTHY" in decision.row.add["reasons"]
    assert decision.row.outcome == OUTCOME_TRIM and "TRIM_CROWDING_ACTIVE" in decision.row.reasons
    assert decision.pending_add is None


def test_euphoria_blocks_the_add(trail_add, composition):
    euphoric = replace(composition.euphoria, flagged=True)
    assert not euphoric.complete  # systemic_euphoria is DISCRETIONARY: the V4 mapping reads flagged
    decision = redecide(trail_add, euphoria=euphoric)
    assert decision.row.add["rulebook_24"]["euphoria"] is True
    assert decision.row.add["reasons"] == [REASON_RULEBOOK_24_NO_ADDING]
    assert decision.row.outcome == OUTCOME_TRAIL and decision.pending_add is None


@pytest.mark.parametrize("flag", ["stress", "euphoria"])
def test_an_unknown_flag_blocks_the_add(trail_add, composition, flag):
    if flag == "stress":
        changes = {"stress_mapped": None}
    else:
        changes = {"euphoria": replace(composition.euphoria, inputs=replace(composition.euphoria.inputs, upside_return=None))}
    decision = redecide(trail_add, **changes)
    assert decision.row.add["rulebook_24"][flag] is None
    assert decision.row.add["reasons"] == [REASON_RULEBOOK_24_FLAG_UNKNOWN]
    assert decision.pending_add is None


def test_an_unknown_crowding_state_blocks_through_btc_154(trail_add, composition):
    unknown = replace(composition.crowding, complete=False)
    decision = redecide(trail_add, crowding=unknown)
    assert decision.row.add["rulebook_24"]["crowding"] is None
    assert REASON_RULEBOOK_24_FLAG_UNKNOWN in decision.row.add["reasons"] and "ADD_REQUIREMENTS_INPUT_MISSING" in decision.row.add["reasons"]
    assert decision.pending_add is None


def test_a_data_quality_failure_blocks_the_add_and_is_exit_evidence(trail_add):
    failure = DataQualityFailure("ohlcv_1h", ("OHLCV_QUALITY_GAP",))
    decision = redecide(trail_add, quality_failures=(failure,))
    assert decision.row.add["data_quality_gate"] == {"action": "HOLD", "data_quality_fail": True}
    assert decision.row.add["reasons"] == [REASON_ADD_DATA_QUALITY_GATE]
    assert decision.pending_add is None
    # DATA_QUALITY_FAIL is not a forced liquidation (spec DATA_RISK_EXIT_PREDICATE)
    assert decision.row.outcome == OUTCOME_TRAIL


@pytest.fixture(scope="module")
def stressed():
    """Through the engine: STRESS at the trail-and-add instant."""

    market = management_market(end=utc(2024, 4, 8))
    inputs = market.build()

    def setup(interventions: Interventions) -> None:
        higher_low_at(interventions, inputs, {TRAIL_AT})
        add_score_lifted(interventions, {TRAIL_AT})
        interventions.inputs(entry_composer, "calculate_stress_flag", {TRAIL_AT}, **STRESS_VALUES)

    return managed_run(market, engine_end=utc(2024, 4, 3, 6), setup=setup)


def test_no_add_reaches_the_engine_while_stress_is_active(stressed):
    row = stressed.rows()[TRAIL_AT]
    assert ("calculate_stress_flag", TRAIL_AT) in stressed.applied
    assert row.add["rulebook_24"]["stress"] is True and REASON_RULEBOOK_24_NO_ADDING in row.add["reasons"]
    assert row.outcome == OUTCOME_TRAIL
    assert stressed.champion.add_followups == ()
    assert not stressed.events(action="ADD")
    assert [event.status for event in stressed.events(event_type="TRAILING_STOP")] == ["APPLIED"]
