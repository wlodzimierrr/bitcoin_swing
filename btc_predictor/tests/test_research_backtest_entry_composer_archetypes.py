"""RBT-004: every long setup archetype, its geometry and the setup-clash rulings.

Setup A arms end to end on a deterministic synthetic market (found by an offline
scan of ``trending_close`` parameters; every outcome is asserted here, never
assumed). Setups B and C need market states that a smooth synthetic market does
not produce together with Entry Conviction >= 80: a *fresh* reclaim at the
decision instant, and a 12 % capitulation. Those tests use **input
interventions**, each named in its test: the real owner is always called, and
only the stated composer-supplied input (or, for the higher-low trigger, the
stated trigger fields) is substituted at the stated instant. Everything else -
the composer's mappings, the 14-day episode, the freshness rules, geometry, the
gates and the intent - runs unchanged. The reclaim freshness rule itself is
tested without intervention, on a natural reclaim that confirms at one instant
and is stale at the next. Setup D is inert and never trades (policy V7 section
6A.6, long-only).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from btc_predictor.backtest.engine import ARM_ENTRY_ACTION, run_backtest
from btc_predictor.features.setup import (
    BEARISH_DISTRIBUTION_SETUP,
    BULL_TREND_CONTINUATION_SETUP,
    BULLISH_RESET_SETUP,
    CAPITULATION_REVERSAL_SETUP,
)
from btc_predictor.levels.breakout import RECLAIM_LEVEL_TYPE
from btc_predictor.levels.swing import WEEKLY_SWING_LOW
from btc_predictor.research_backtest import entry_composer
from btc_predictor.risk.invalidation import SELECTION_FARTHEST, SELECTION_NEAREST
from btc_predictor.research_backtest.entry_composer import (
    LONG_ARCHETYPES,
    OUTCOME_ARM_ENTRY,
    OUTCOME_NO_TRADE,
    REASON_HARD_VETO,
    REASON_POSITION_ALREADY_OPEN,
    REASON_SETUP_GEOMETRY_CONFLICT,
    TRADE_BAND_ACTIONS,
    EntryComposer,
)
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, HOUR, Scenario, decide_consecutively, recording, trending_close, utc

RECORDED = (
    "detect_bull_trend_continuation", "detect_bullish_reset", "detect_capitulation_reversal", "detect_bearish_distribution",
    "select_structural_invalidation", "initial_stop_for_setup", "evaluate_hard_veto", "apply_no_chase_filter",
)


def _market(amplitude: float, period: float, drift: float, end) -> Scenario:
    return Scenario(end=end, close_at=trending_close(daily_drift=drift, cycle_days=period, cycle_amplitude=amplitude))


class Interventions:
    """Substitute stated owner inputs at stated decision instants; the real owners always run."""

    def __init__(self, composer: EntryComposer, patch: pytest.MonkeyPatch) -> None:
        self.instant = None
        self.applied: list[tuple[str, object]] = []
        self._patch = patch
        decide = composer.decide

        def tracking(instant, **kwargs):
            self.instant = instant
            return decide(instant, **kwargs)

        composer.decide = tracking  # type: ignore[method-assign]

    def inputs(self, name: str, at: set, **changes: object) -> None:
        real = getattr(entry_composer, name)

        def wrapper(inputs, *args, **kwargs):
            if self.instant in at:
                inputs = replace(inputs, **changes)
                self.applied.append((name, self.instant))
            return real(inputs, *args, **kwargs)

        self._patch.setattr(entry_composer, name, wrapper)

    def trigger_fields(self, name: str, at: set, **changes: object) -> None:
        real = getattr(entry_composer, name)

        def wrapper(*args, **kwargs):
            result = real(*args, **kwargs)
            if self.instant in at:
                self.applied.append((name, self.instant))
                return replace(result, **{key: (self.instant if value == "t" else value) for key, value in changes.items()})
            return result

        self._patch.setattr(entry_composer, name, wrapper)


def _run(scenario: Scenario, first, last, setup=None):
    inputs = scenario.build()
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    # recording first, so the interventions unwind before it restores the real owners
    with recording(*RECORDED) as calls, pytest.MonkeyPatch.context() as patch:
        interventions = Interventions(composer, patch)
        if setup is not None:
            setup(interventions, last)
        rows = decide_consecutively(composer, first, last)
    return {"inputs": inputs, "composer": composer, "rows": rows, "calls": calls, "applied": interventions.applied}


def _last(calls, name):
    return calls[name][-1]


def _by_setup(calls, name, setup):
    return [call for call in calls[name] if call.kwargs.get("setup") == setup or getattr(call.args[0], "setup", None) == setup]


CAPITULATION_VALUES = {
    "range_percentile": Decimal("99"),
    "downside_return": Decimal("-0.25"),
    "liquidation_percentile": Decimal("99"),
    "volatility_percentile": Decimal("99"),
    "funding_zscore": Decimal("-3"),
}
STRESS_VALUES = {
    "volatility_percentile": Decimal("99"),
    "liquidation_percentile": Decimal("99"),
    "downside_return": Decimal("-0.2"),
    "funding_zscore": Decimal("-3"),
    "basis_zscore": Decimal("-3"),
}


@pytest.fixture(scope="module")
def runs():
    results = {}
    # A: a natural Setup A entry, no intervention.
    results["A"] = _run(_market(0.07, 80.0, 0.0003, utc(2024, 4, 15)), utc(2024, 3, 25), utc(2024, 3, 31))

    # A + B: Setup A is detected naturally; Setup B fails only on a fresh reclaim.
    # Intervention: BullishResetInput.entry_trigger_confirmed = True at t.
    def fresh_reclaim(interventions, t):
        interventions.inputs("detect_bullish_reset", {t}, entry_trigger_confirmed=True)

    results["AB"] = _run(_market(0.07, 60.0, 0.0006, utc(2024, 7, 14)), utc(2024, 6, 25), utc(2024, 7, 12), fresh_reclaim)
    # B alone: Setup A is not detected; the same Setup B intervention.
    results["B"] = _run(_market(0.1, 60.0, 0.0006, utc(2024, 7, 14)), utc(2024, 6, 25), utc(2024, 7, 12), fresh_reclaim)

    # C alone. Interventions: CapitulationFlagInput takes capitulation values at
    # t - 4..t - 2 days (the real owner flags; the composer's V4 mapping and
    # 14-day episode do the rest); the latest higher-low trigger result reads
    # triggered at t (the composer's freshness rule then confirms); and
    # StressFlagInput takes stress values at t, so Setup A (which requires no
    # STRESS) is not detected while Setup C (which ignores STRESS) is.
    def capitulation_episode(interventions, t):
        interventions.inputs("calculate_capitulation_flag", {t - 4 * DAY, t - 3 * DAY, t - 2 * DAY}, **CAPITULATION_VALUES)
        interventions.trigger_fields("evaluate_higher_low_trigger", {t}, triggered=True, detected_at="t")
        interventions.inputs("calculate_stress_flag", {t}, **STRESS_VALUES)

    capitulation_market = _market(0.1, 35.0, 0.0006, utc(2024, 8, 13))
    results["C"] = _run(capitulation_market, utc(2024, 7, 25), utc(2024, 8, 11), capitulation_episode)

    # C with A: Setup A is detected naturally. Intervention: CapitulationReversalInput
    # takes an active capitulation (since t - 2 days) and a fresh confirmation at t.
    def detected_reversal(interventions, t):
        interventions.inputs(
            "detect_capitulation_reversal", {t},
            capitulation_flagged=True, capitulation_detected_at=t - 2 * DAY, confirmation_triggered=True, confirmation_at=t,
        )

    results["CA"] = _run(capitulation_market, utc(2024, 7, 25), utc(2024, 8, 11), detected_reversal)
    return results


# --- Setup A ---------------------------------------------------------------------------------


def test_setup_a_arms_an_entry_at_the_decision_price(runs):
    run = runs["A"]
    row = run["rows"][-1]
    t = row.decision_at
    assert run["applied"] == []
    assert row.outcome == OUTCOME_ARM_ENTRY and row.setup == BULL_TREND_CONTINUATION_SETUP
    assert row.detected_setups == (BULL_TREND_CONTINUATION_SETUP,) and row.reasons == (BULL_TREND_CONTINUATION_SETUP,)
    price = next(bar for bar in run["inputs"].dataset.price_bars if bar.ingested_at == t).close
    intent = row.intent
    assert intent["action"] == ARM_ENTRY_ACTION and intent["direction"] == "long"
    assert intent["entry_zone_lower"] == intent["entry_zone_upper"] == price  # owner ruling: the point zone
    stop = _by_setup(run["calls"], "initial_stop_for_setup", BULL_TREND_CONTINUATION_SETUP)[-1].result
    assert intent["initial_stop"] == stop.as_record()
    assert stop.entry_price == price and stop.direction == "long" and dict(stop.config_metadata) == dict(CONFIG.run_metadata())
    assert row.entry_conviction >= Decimal("80") and row.entry_action in TRADE_BAND_ACTIONS
    assert intent["entry_conviction"] == row.entry_conviction
    # K_entry for RBT-005's regime-invalidation predicate is persisted on the row
    assert row.regime["classification"] is not None and row.regime["complete"] is True
    veto = _last(run["calls"], "evaluate_hard_veto")
    assert veto.args[0].setup == BULL_TREND_CONTINUATION_SETUP and not veto.result.blocked
    assert row.unaccounted == ()


def test_setups_a_and_b_share_the_nearest_zone_and_c_uses_the_farthest(runs):
    calls = runs["A"]["calls"]
    modes = {}
    for setup in LONG_ARCHETYPES:
        result = [call.result for call in calls["select_structural_invalidation"] if call.kwargs["setup"] == setup][-1]
        modes[setup] = result.selection_mode
    assert modes == {
        BULL_TREND_CONTINUATION_SETUP: SELECTION_NEAREST,
        BULLISH_RESET_SETUP: SELECTION_NEAREST,
        CAPITULATION_REVERSAL_SETUP: SELECTION_FARTHEST,
    }


def test_the_armed_entry_fills_through_the_engine():
    inputs = _market(0.07, 80.0, 0.0003, utc(2024, 4, 15)).build()
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    bars = tuple(bar for bar in inputs.dataset.price_bars if utc(2024, 3, 24, 23) <= bar.timestamp < utc(2024, 4, 2, 1))
    result = run_backtest(bars, strategy=composer, strategy_config=CONFIG, symbol=bars[0].symbol)
    rows = composer.ledger
    armed = [row for row in rows if row.outcome == OUTCOME_ARM_ENTRY]
    assert [row.decision_at for row in armed] == [utc(2024, 3, 31)]
    fills = [event for event in result.events if event.event_type == "ENTRY_EXECUTION" and "ENTRY_EXECUTION_FILLED" in event.reason_codes]
    assert len(fills) == 1 and fills[0].status == "EXECUTED"
    assert fills[0].occurred_at == utc(2024, 3, 31, 1)  # the next bar trades through the point zone
    assert fills[0].source_id == armed[0].intent["source_id"]
    # the next decision instant sees the open position
    after = [row for row in rows if row.decision_at > utc(2024, 3, 31)]
    assert after and all(row.position_open and row.reasons == (REASON_POSITION_ALREADY_OPEN,) for row in after if row.position_open)
    assert any(row.position_open for row in after)


# --- Setups A and B together, and B alone -------------------------------------------------------


def test_a_and_b_together_trade_once_labelled_a(runs):
    run = runs["AB"]
    t = run["rows"][-1].decision_at
    assert run["applied"] == [("detect_bullish_reset", t)]
    row = run["rows"][-1]
    assert row.detected_setups == (BULL_TREND_CONTINUATION_SETUP, BULLISH_RESET_SETUP)
    assert row.outcome == OUTCOME_ARM_ENTRY and row.setup == BULL_TREND_CONTINUATION_SETUP
    stops = {setup: _by_setup(run["calls"], "initial_stop_for_setup", setup)[-1].result for setup in (BULL_TREND_CONTINUATION_SETUP, BULLISH_RESET_SETUP)}
    # one shared geometry, so one trade
    assert stops[BULL_TREND_CONTINUATION_SETUP].stop_price == stops[BULLISH_RESET_SETUP].stop_price
    assert row.intent["initial_stop"]["stop_price"] == format(stops[BULL_TREND_CONTINUATION_SETUP].stop_price, "f")
    assert row.unaccounted == ()


def test_setup_b_reaches_the_gates_on_its_own_geometry(runs):
    run = runs["B"]
    row = run["rows"][-1]
    assert run["applied"] == [("detect_bullish_reset", row.decision_at)]
    assert row.detected_setups == (BULLISH_RESET_SETUP,) and row.setup == BULLISH_RESET_SETUP
    veto = _last(run["calls"], "evaluate_hard_veto")
    assert veto.args[0].setup == BULLISH_RESET_SETUP
    invalidation = [call.result for call in run["calls"]["select_structural_invalidation"] if call.kwargs["setup"] == BULLISH_RESET_SETUP][-1]
    no_chase = _last(run["calls"], "apply_no_chase_filter")
    assert no_chase.args[0].cluster_id == invalidation.selected_cluster_id  # the invalidation-selected support zone
    # this market is far above that zone: the no-chase veto blocks the trade
    assert row.outcome == OUTCOME_NO_TRADE and REASON_HARD_VETO in row.reasons
    assert "HARD_VETO_NO_CHASE_VIOLATION" in veto.result.reason_codes and veto.args[0].no_chase_blocked is True
    assert row.intent is None and row.unaccounted == ()


# --- Setup C, and C with A ------------------------------------------------------------------------


def test_setup_c_arms_on_its_episode_and_the_farthest_zone(runs):
    run = runs["C"]
    row = run["rows"][-1]
    t = row.decision_at
    assert ("calculate_capitulation_flag", t - 4 * DAY) in run["applied"] and ("evaluate_higher_low_trigger", t) in run["applied"]
    states = {item.decision_at: item.capitulation_flag_state for item in run["rows"]}
    assert [states[t - offset * DAY] for offset in (5, 4, 3, 2, 1, 0)] == [False, True, True, True, False, False]
    reversal = _last(run["calls"], "detect_capitulation_reversal").args[0]
    # owner ruling: the first instant of the consecutive flagged run, and a fresh confirmation
    assert reversal.capitulation_flagged is True and reversal.capitulation_detected_at == t - 4 * DAY
    assert reversal.confirmation_triggered is True and reversal.confirmation_at == t
    assert row.detected_setups == (CAPITULATION_REVERSAL_SETUP,)
    assert row.outcome == OUTCOME_ARM_ENTRY and row.setup == CAPITULATION_REVERSAL_SETUP
    stop = _by_setup(run["calls"], "initial_stop_for_setup", CAPITULATION_REVERSAL_SETUP)[-1].result
    assert row.intent["initial_stop"] == stop.as_record()
    # STRESS is active and mapped (V4: only the DISCRETIONARY input is missing),
    # but the champion configuration does not let STRESS block new trades.
    assert row.flags["stress"]["mapped"] is True and "STRESS_INPUT_MISSING" in row.flags["stress"]["reason_codes"]
    veto = _last(run["calls"], "evaluate_hard_veto")
    assert veto.args[0].stress_flagged is True and "STRESS_INPUT_MISSING" in veto.args[0].source_reason_codes["stress_flagged"]
    assert CONFIG.volatility_flags.stress.block_new_trades is False and not veto.result.blocked
    assert "BULL_TREND_CONTINUATION_STRESS_ACTIVE" in row.owner_reason_codes[f"setup:{BULL_TREND_CONTINUATION_SETUP}"]["reason_codes"]
    assert row.unaccounted == ()


def test_setup_c_with_a_or_b_is_a_geometry_conflict(runs):
    run = runs["CA"]
    row = run["rows"][-1]
    assert run["applied"] == [("detect_capitulation_reversal", row.decision_at)]
    assert row.detected_setups == (BULL_TREND_CONTINUATION_SETUP, CAPITULATION_REVERSAL_SETUP)
    assert row.outcome == OUTCOME_NO_TRADE and row.reasons == (REASON_SETUP_GEOMETRY_CONFLICT,)
    assert row.intent is None and row.setup is None and "hard_veto" not in row.owner_reason_codes
    # the conflict is one of invalidation policy (NEAREST against FARTHEST), even
    # when, as here, both policies select the same support zone
    modes = {call.kwargs["setup"]: call.result.selection_mode for call in run["calls"]["select_structural_invalidation"][-3:]}
    assert modes[BULL_TREND_CONTINUATION_SETUP] == SELECTION_NEAREST and modes[CAPITULATION_REVERSAL_SETUP] == SELECTION_FARTHEST


# --- Setup D and the long-only scope ------------------------------------------------------------


def test_setup_d_is_called_with_inert_inputs_and_never_trades(runs):
    total = 0
    for run in runs.values():
        for call in run["calls"]["detect_bearish_distribution"]:
            total += 1
            assert call.args[0].distribution_flagged is None and call.args[0].short_trigger_confirmed is None
            assert call.args[0].risk_reward is None
            assert not call.result.detected
        for row in run["rows"]:
            assert BEARISH_DISTRIBUTION_SETUP not in row.detected_setups and row.setup != BEARISH_DISTRIBUTION_SETUP
            assert row.intent is None or row.intent["direction"] == "long"
    assert total > 50
    assert entry_composer.accounted_cause("BEARISH_DISTRIBUTION_INPUT_MISSING").cause == "INERT_SHORT_SIDE"
    assert CONFIG.backtest.allow_short_trades is False


# --- the trigger freshness rulings, on real owner outputs -----------------------------------------


@pytest.fixture(scope="module")
def triggers():
    # A natural fresh higher-low confirmation at 2024-07-22 in this market.
    inputs = _market(0.07, 60.0, 0.0012, utc(2024, 7, 24)).build()
    rows = {}
    with recording("evaluate_higher_low_trigger", "detect_capitulation_reversal") as calls:
        for instant in (utc(2024, 7, 21), utc(2024, 7, 22)):
            start = {name: len(calls[name]) for name in calls}
            rows[instant] = (EntryComposer(inputs, strategy_config=CONFIG).decide(instant).row, {name: calls[name][start[name]:] for name in calls})
    return rows


def test_the_higher_low_confirmation_must_be_fresh(triggers):
    stale_row, stale = triggers[utc(2024, 7, 21)]
    fresh_row, fresh = triggers[utc(2024, 7, 22)]
    (stale_trigger,) = stale["evaluate_higher_low_trigger"]
    (fresh_trigger,) = fresh["evaluate_higher_low_trigger"]
    # the owner keeps reporting an older confirmation as triggered...
    assert stale_trigger.result.triggered and stale_trigger.result.detected_at < utc(2024, 7, 21)
    # ...but only a confirmation detected at t confirms Setup C
    assert stale["detect_capitulation_reversal"][0].args[0].confirmation_triggered is False
    assert stale["detect_capitulation_reversal"][0].args[0].confirmation_at is None
    assert fresh_trigger.result.triggered and fresh_trigger.result.detected_at == utc(2024, 7, 22)
    assert fresh["detect_capitulation_reversal"][0].args[0].confirmation_triggered is True
    assert fresh["detect_capitulation_reversal"][0].args[0].confirmation_at == utc(2024, 7, 22)
    # the source is the latest weekly swing low detected by t
    source = fresh_trigger.args[0]
    assert source.level_type == WEEKLY_SWING_LOW
    assert source.detected_at <= utc(2024, 7, 22)


@pytest.fixture(scope="module")
def reclaims():
    # A market whose reclaim level (detected 2024-11-02) confirms naturally on
    # 2024-11-03 (found by the offline scan); no input is substituted.
    inputs = _market(0.18, 35.0, 0.0003, utc(2024, 11, 10)).build()
    found = {}
    for instant in (utc(2024, 11, 2), utc(2024, 11, 3), utc(2024, 11, 4)):
        with recording("evaluate_reclaim_trigger", "detect_bullish_reset") as calls:
            EntryComposer(inputs, strategy_config=CONFIG).decide(instant)
        found[instant] = calls
    return found


def test_the_reclaim_trigger_must_be_fresh(reclaims):
    """Setup B's entry_trigger_confirmed (owner ruling: fresh at this instant): the
    latest reclaim level's trigger, None while pending, True only when confirmed
    with detected_at == t."""

    def observed(instant):
        calls = reclaims[instant]
        (trigger,) = calls["evaluate_reclaim_trigger"]
        (reset,) = calls["detect_bullish_reset"]
        return trigger.args[0], trigger.result, reset.args[0].entry_trigger_confirmed

    pending_level, pending, pending_confirmed = observed(utc(2024, 11, 2))
    fresh_level, fresh, fresh_confirmed = observed(utc(2024, 11, 3))
    stale_level, stale, stale_confirmed = observed(utc(2024, 11, 4))
    # the same reclaim level (only its source bar count grows) is evaluated each time
    def key(level):
        return level.level_type, level.level_timestamp, level.confirmation_timestamp, level.detected_at, level.price

    assert key(pending_level) == key(fresh_level) == key(stale_level)
    assert pending_level.level_type == RECLAIM_LEVEL_TYPE
    assert pending_level.detected_at == utc(2024, 11, 2)
    # pending: the owner's result is incomplete, so the input is unknown
    assert not pending.complete
    assert pending_confirmed is None
    # fresh: confirmed and detected at t
    assert fresh.complete and fresh.triggered and fresh.detected_at == utc(2024, 11, 3)
    assert fresh_confirmed is True
    # stale: the owner keeps reporting the earlier confirmation, which no longer confirms
    assert stale.complete and stale.triggered and stale.detected_at == utc(2024, 11, 3)
    assert stale_confirmed is False
