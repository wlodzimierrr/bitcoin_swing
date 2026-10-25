"""RBT-004: every hard veto and gate (Rulebook 14/24/25, BTC-143, policy V7 section 7).

Each veto is exercised through the composer on a deterministic synthetic market
in which Setup A arms (or a setup is otherwise detected), and the exact
``HardVetoInput`` the composer builds is recorded. Where a veto needs a state
the synthetic market does not reach (severe crowding), the test names its
**input intervention**: the real owner runs on the stated substituted inputs.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from btc_predictor.features.setup import BULL_TREND_CONTINUATION_SETUP, BULLISH_RESET_SETUP
from btc_predictor.research_backtest import entry_composer
from btc_predictor.research_backtest.entry_composer import (
    OUTCOME_ARM_ENTRY,
    OUTCOME_NO_TRADE,
    OUTCOME_STRUCTURALLY_UNEVALUABLE,
    REASON_DATA_QUALITY_GATE,
    REASON_ENTRY_CONVICTION_BELOW_TRADE_BAND,
    REASON_HARD_VETO,
    REASON_NO_SETUP_DETECTED,
    REASON_NO_VALID_STRUCTURAL_STOP,
    EntryComposer,
    accounted_cause,
)
from btc_predictor.signals.hard_veto import HardVetoInput, evaluate_hard_veto
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, HOUR, Scenario, decide_consecutively, recording, trending_close, utc

RECORDED = ("evaluate_hard_veto", "apply_no_chase_filter", "apply_data_quality_gate", "reward_risk_for_stop", "detect_bull_trend_continuation", "calculate_stress_flag")
ARM = utc(2024, 3, 31)


def _market(amplitude, period, drift, end):
    return Scenario(end=end, close_at=trending_close(daily_drift=drift, cycle_days=period, cycle_amplitude=amplitude))


def _armed_market():
    return _market(0.07, 80.0, 0.0003, utc(2024, 4, 15))


def _decide(inputs, first, last, *, interventions=()):
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    # recording first, so the interventions unwind before it restores the real owners
    with recording(*RECORDED) as calls, pytest.MonkeyPatch.context() as patch:
        for name, at, changes in interventions:
            real = getattr(entry_composer, name)
            decide = composer.decide
            state = {"instant": None}

            def tracking(instant, _decide=decide, _state=state, **kwargs):
                _state["instant"] = instant
                return _decide(instant, **kwargs)

            composer.decide = tracking  # type: ignore[method-assign]

            def wrapper(inputs, *args, _real=real, _state=state, _at=at, _changes=changes, **kwargs):
                if _state["instant"] in _at:
                    inputs = replace(inputs, **_changes)
                return _real(inputs, *args, **kwargs)

            patch.setattr(entry_composer, name, wrapper)
        rows = decide_consecutively(composer, first, last)
    return rows, calls


@pytest.fixture(scope="module")
def armed():
    inputs = _armed_market().build()
    rows, calls = _decide(inputs, utc(2024, 3, 25), ARM)
    return {"inputs": inputs, "rows": rows, "calls": calls}


def _veto_input(calls) -> HardVetoInput:
    return calls["evaluate_hard_veto"][-1].args[0]


# --- the veto input the composer builds ---------------------------------------------------------


def test_the_hard_veto_input_maps_every_owner_result(armed):
    row = armed["rows"][-1]
    assert row.outcome == OUTCOME_ARM_ENTRY
    calls = armed["calls"]
    veto_input = _veto_input(calls)
    assert veto_input.setup == BULL_TREND_CONTINUATION_SETUP
    assert veto_input.data_quality_fail is False and row.data_quality["data_quality_fail"] is False
    assert veto_input.valid_structural_stop is True  # the setup's stop is complete
    reward = [call.result for call in calls["reward_risk_for_stop"] if call.kwargs["setup"] == BULL_TREND_CONTINUATION_SETUP][-1]
    assert veto_input.reward_risk_passes is reward.passes is True
    no_chase = calls["apply_no_chase_filter"][-1].result
    assert veto_input.no_chase_blocked is no_chase.blocked is False
    assert veto_input.severe_crowding_flagged is row.flags["crowding"]["severe_crowding_state"] is False
    # policy V7 section 7: only the DISCRETIONARY systemic_shock is missing, so
    # StressFlagResult.flagged passes, with STRESS_INPUT_MISSING as evidence
    stress = calls["calculate_stress_flag"][-1]
    assert stress.args[0].systemic_shock is None and not stress.result.complete
    assert veto_input.stress_flagged is stress.result.flagged is False
    assert "STRESS_INPUT_MISSING" in veto_input.source_reason_codes["stress_flagged"]
    assert set(veto_input.source_reason_codes) == {
        "data_quality_fail", "valid_structural_stop", "reward_risk_passes", "stress_flagged", "severe_crowding_flagged", "no_chase_blocked", "setup",
    }
    assert calls["evaluate_hard_veto"][-1].result.reason_codes == ("HARD_VETO_CLEAR",)
    gate = calls["apply_data_quality_gate"][-1]
    assert gate.args[0] == "ENTER" and gate.result.action == "ENTER" and row.data_quality["gate"]["action"] == "ENTER"


def test_a_non_discretionary_stress_input_fails_the_veto_closed():
    # STRESS_NON_DISCRETIONARY_MISSING: the composer passes None; the frozen
    # veto owner then refuses (every such input also feeds an Entry Conviction
    # component, so in composition the instant is already unevaluable).
    inputs = HardVetoInput(
        data_quality_fail=False, valid_structural_stop=True, reward_risk_passes=True, stress_flagged=None,
        severe_crowding_flagged=False, no_chase_blocked=False, setup=BULL_TREND_CONTINUATION_SETUP,
    )
    result = evaluate_hard_veto(inputs, strategy_config=CONFIG)
    assert result.blocked and "HARD_VETO_INPUT_MISSING" in result.reason_codes


def test_stress_never_blocks_a_new_trade_under_the_champion_configuration():
    assert CONFIG.volatility_flags.stress.block_new_trades is False
    inputs = HardVetoInput(
        data_quality_fail=False, valid_structural_stop=True, reward_risk_passes=True, stress_flagged=True,
        severe_crowding_flagged=False, no_chase_blocked=False, setup=BULL_TREND_CONTINUATION_SETUP,
    )
    assert not evaluate_hard_veto(inputs, strategy_config=CONFIG).blocked


# --- DATA_QUALITY_FAIL (owner ruling: the last completed UTC day) ---------------------------------


@pytest.fixture(scope="module")
def stale_derivatives(armed):
    # The perpetual-volume feed stops six hours before t: a derivatives data-quality
    # failure that changes no other input of the composition.
    shared = armed["inputs"].dataset.shared_snapshot
    kept = tuple(row for row in shared.perp_volumes if not ARM - 6 * HOUR < row.observation_time <= ARM)
    inputs = replace(armed["inputs"], dataset=replace(armed["inputs"].dataset, shared_snapshot=replace(shared, perp_volumes=kept)))
    rows, calls = _decide(inputs, utc(2024, 3, 25), ARM)
    return rows, calls


def test_a_data_quality_failure_vetoes_and_gates_the_entry(stale_derivatives, armed):
    rows, calls = stale_derivatives
    row = rows[-1]
    assert row.detected_setups == armed["rows"][-1].detected_setups == (BULL_TREND_CONTINUATION_SETUP,)
    assert row.data_quality["data_quality_fail"] is True
    assert [failure["source_component"] for failure in row.data_quality["failures"]] == ["derivatives"]
    veto_input = _veto_input(calls)
    assert veto_input.data_quality_fail is True and veto_input.source_reason_codes["data_quality_fail"]
    assert "HARD_VETO_DATA_QUALITY_FAIL" in calls["evaluate_hard_veto"][-1].result.reason_codes
    assert row.data_quality["gate"]["action"] != "ENTER"
    assert row.outcome == OUTCOME_NO_TRADE and row.reasons == (REASON_HARD_VETO, REASON_DATA_QUALITY_GATE)
    assert row.intent is None and row.unaccounted == ()
    # every other component is unchanged
    assert row.components == armed["rows"][-1].components


@pytest.fixture(scope="module")
def ohlcv_gaps():
    t = utc(2024, 4, 9)
    inside = Scenario(missing_hours=(utc(2024, 4, 8, 12),)).composer().decide(t).row
    older = Scenario(missing_hours=(utc(2024, 4, 7, 12),)).composer().decide(t).row
    return inside, older


def test_an_ohlcv_gap_fails_data_quality_only_inside_the_last_completed_day(ohlcv_gaps):
    inside, older = ohlcv_gaps
    assert inside.data_quality["window_start"] == utc(2024, 4, 8) and inside.data_quality["window_end"] == utc(2024, 4, 9)
    assert inside.data_quality["data_quality_fail"] is True
    assert "ohlcv_1h" in [failure["source_component"] for failure in inside.data_quality["failures"]]
    assert "ohlcv_1h" not in [failure["source_component"] for failure in older.data_quality["failures"]]
    assert older.data_quality["data_quality_fail"] is False
    assert inside.unaccounted == () and older.unaccounted == ()


# --- no-chase ---------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def chased():
    inputs = _market(0.07, 80.0, 0.0006, utc(2024, 4, 15)).build()
    return _decide(inputs, utc(2024, 3, 25), utc(2024, 4, 1))


def test_the_no_chase_filter_vetoes_an_extended_entry(chased):
    rows, calls = chased
    row = rows[-1]
    assert row.detected_setups == (BULL_TREND_CONTINUATION_SETUP,)
    no_chase = calls["apply_no_chase_filter"][-1]
    assert no_chase.result.blocked is True and no_chase.kwargs["direction"] == "long"
    # P_t, available at t, against the invalidation-selected support zone
    assert no_chase.kwargs["current_price_available_at"] == no_chase.kwargs["as_of"] == row.decision_at
    assert _veto_input(calls).no_chase_blocked is True
    assert "HARD_VETO_NO_CHASE_VIOLATION" in calls["evaluate_hard_veto"][-1].result.reason_codes
    assert row.outcome == OUTCOME_NO_TRADE and row.reasons == (REASON_HARD_VETO,) and row.intent is None
    # the ATR distance mode of the champion config uses the composer's ATR at t
    mode = CONFIG.entry_triggers.no_chase.distance_mode
    assert no_chase.kwargs["distance_mode"] == mode
    assert (no_chase.kwargs["atr"] is not None) == (mode == "atr")


# --- the BTC-143 reward/risk filter -------------------------------------------------------------------


@pytest.fixture(scope="module")
def default_rows():
    composer = Scenario().composer()
    with recording(*RECORDED) as calls:
        row = composer.decide(utc(2024, 4, 9)).row
    return row, calls


def test_a_reward_risk_below_the_setup_minimum_detects_no_setup(default_rows):
    row, calls = default_rows
    reward = [call.result for call in calls["reward_risk_for_stop"] if call.kwargs["setup"] == BULL_TREND_CONTINUATION_SETUP][-1]
    minimum = Decimal(str(CONFIG.setup_requirements.bull_trend_continuation["minimum_rr"]))
    assert reward.complete and reward.passes is False and reward.reward_risk < minimum
    detection = calls["detect_bull_trend_continuation"][-1]
    assert detection.args[0].risk_reward == reward.reward_risk
    assert detection.result.reason_codes == ("BULL_TREND_CONTINUATION_RR_TOO_LOW",)
    assert row.outcome == OUTCOME_NO_TRADE and row.reasons == (REASON_NO_SETUP_DETECTED,)
    # every archetype's filter runs on its own stop, with the measured move omitted (spec)
    for call in calls["reward_risk_for_stop"]:
        assert call.kwargs["measured_move"] is None and call.kwargs["config"] is CONFIG


def test_no_reward_reference_is_an_accounted_cause():
    composer = _market(0.07, 35.0, 0.0006, utc(2024, 10, 19)).composer()
    with recording("reward_risk_for_stop", "detect_bull_trend_continuation") as calls:
        row = composer.decide(utc(2024, 10, 17)).row
    reward = [call.result for call in calls["reward_risk_for_stop"] if call.kwargs["setup"] == BULL_TREND_CONTINUATION_SETUP][-1]
    assert reward.reward_risk is None and "REWARD_RISK_NO_REWARD_REFERENCE" in reward.reason_codes
    assert accounted_cause("REWARD_RISK_NO_REWARD_REFERENCE").reference == "MEASURED_MOVE_REFERENCE"
    assert calls["detect_bull_trend_continuation"][-1].args[0].risk_reward is None
    assert row.unaccounted == ()


# --- severe crowding (SEVERE_CROWDING_STATE = CROWDING.flagged if complete) ------------------------------

CROWDED = {"funding_zscore": Decimal("3"), "basis_zscore": Decimal("3"), "oi_intensity_percentile": Decimal("99")}


@pytest.fixture(scope="module")
def crowded_a(armed):
    # Input intervention: CrowdingFlagInput takes crowded values at t; the real owner flags.
    return _decide(armed["inputs"], utc(2024, 3, 25), ARM, interventions=(("calculate_crowding_flag", {ARM}, CROWDED),))


def test_severe_crowding_stops_setup_a(crowded_a):
    rows, calls = crowded_a
    row = rows[-1]
    assert row.flags["crowding"]["flagged"] is True and row.flags["crowding"]["complete"] is True
    assert row.flags["crowding"]["severe_crowding_state"] is True
    detection = calls["detect_bull_trend_continuation"][-1]
    assert detection.args[0].severe_crowding_flagged is True
    assert any("CROWDING" in code for code in detection.result.reason_codes)
    assert row.outcome == OUTCOME_NO_TRADE and row.reasons == (REASON_NO_SETUP_DETECTED,)


@pytest.fixture(scope="module")
def crowded_b():
    # Setup B does not check crowding itself, so the hard veto must. Input
    # interventions: BullishResetInput.entry_trigger_confirmed = True and the
    # crowded CrowdingFlagInput, both at t.
    t = utc(2024, 7, 12)
    inputs = _market(0.1, 60.0, 0.0006, utc(2024, 7, 14)).build()
    return _decide(
        inputs, utc(2024, 6, 25), t,
        interventions=(("detect_bullish_reset", {t}, {"entry_trigger_confirmed": True}), ("calculate_crowding_flag", {t}, CROWDED)),
    )


def test_severe_crowding_vetoes_a_setup_that_does_not_check_it(crowded_b):
    rows, calls = crowded_b
    row = rows[-1]
    assert row.detected_setups == (BULLISH_RESET_SETUP,)
    assert _veto_input(calls).severe_crowding_flagged is True
    assert "HARD_VETO_SEVERE_CROWDING" in calls["evaluate_hard_veto"][-1].result.reason_codes
    assert row.outcome == OUTCOME_NO_TRADE and REASON_HARD_VETO in row.reasons


# --- Entry Conviction below the trade band, and no valid structural stop -----------------------------------


@pytest.fixture(scope="module")
def watch_band():
    inputs = _market(0.07, 35.0, 0.0006, utc(2024, 8, 13)).build()
    return _decide(inputs, utc(2024, 7, 25), utc(2024, 8, 12))


def test_entry_conviction_below_the_trade_band_is_no_trade(watch_band):
    rows, calls = watch_band
    row = [row for row in rows if row.decision_at == utc(2024, 8, 11)][0]
    assert row.detected_setups == (BULL_TREND_CONTINUATION_SETUP,)
    assert row.entry_conviction < Decimal("80") and row.entry_action not in entry_composer.TRADE_BAND_ACTIONS
    assert row.outcome == OUTCOME_NO_TRADE and row.reasons == (REASON_ENTRY_CONVICTION_BELOW_TRADE_BAND,)
    assert row.intent is None


def test_no_valid_stop_from_geometry_is_no_trade(watch_band, armed):
    for row in (armed["rows"][2], [row for row in watch_band[0] if row.decision_at == utc(2024, 8, 12)][0]):
        assert row.outcome == OUTCOME_NO_TRADE and row.reasons == (REASON_NO_VALID_STRUCTURAL_STOP,), row.decision_at
        assert row.components["structure"] is None
        assert all(value is not None for name, value in row.components.items() if name != "structure")
        stops = {label: codes for label, codes in row.owner_reason_codes.items() if label.startswith("stop:")}
        assert stops and not any(codes["complete"] for codes in stops.values())
        assert not ({code for codes in row.owner_reason_codes.values() for code in codes["reason_codes"]} & entry_composer._STOP_DATA_CAUSES)
        assert row.unevaluable == () and row.unaccounted == ()


def test_no_valid_stop_from_missing_data_is_structurally_unevaluable():
    row = Scenario(missing_hours=(utc(2024, 4, 5, 12),)).composer().decide(utc(2024, 4, 9)).row
    assert row.outcome == OUTCOME_STRUCTURALLY_UNEVALUABLE and row.reasons == ("STRUCTURE_INCOMPLETE",)
    assert {item.component: item.causes for item in row.unevaluable} == {"structure": ("VOLATILITY_BUFFER_INPUT_MISSING",)}
    assert row.owner_reason_codes["stop:BULL_TREND_CONTINUATION"]["reason_codes"] == ["INITIAL_STOP_BUFFER_INCOMPLETE"]
    assert row.unaccounted == ()
