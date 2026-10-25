"""RBT-004 core contract: the decision ledger, determinism, the engine adapter and accounting.

One ledger row per daily decision instant, nothing zero-filled, a canonical
and deterministic serialisation, the BTC-180 strategy adapter, the policy V7
section 5A.6 runtime completeness guard and its accounting against the bound
inventory and spec. Synthetic deterministic fixtures only.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.backtest.engine import run_backtest
from btc_predictor.config import load_strategy_config
from btc_predictor.features import positioning as positioning_owner
from btc_predictor.features.regime import REGIME_MODEL_CORE_MARKET_ONLY, RegimeSmoothingInput, calculate_regime_smoothing
from btc_predictor.research_backtest import completion_spec, entry_composer
from btc_predictor.research_backtest.replay_inputs import canonical_json_bytes
from btc_predictor.research_backtest.entry_composer import (
    AUTHORITY_INVENTORY_MINIMUM_HISTORY,
    AUTHORITY_INVENTORY_ROW,
    AUTHORITY_SPEC_ENTRY,
    AUTHORITY_SPEC_GUARD,
    CAUSE_ACCOUNTING,
    CAUSE_DECISION_PRICE_BAR_MISSING,
    CAUSE_LIQUIDATION_PERCENTILE_MISSING,
    COMPLETION_SPEC_SHA256,
    FEATURE_NAMES,
    OUTCOME_NO_TRADE,
    OUTCOME_STRUCTURALLY_UNEVALUABLE,
    OUTCOMES,
    REASON_POSITION_ALREADY_OPEN,
    EntryComposer,
    EntryComposerError,
    EntryComposerInputs,
    LiquidationPercentileObservation,
    _DecisionRun,
    accounted_cause,
)
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, HOUR, Scenario, recording, utc, with_inputs

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = completion_spec.ARTIFACT_DIRECTORY
SPEC = json.loads((ARTIFACTS / completion_spec.SPEC_FILENAME).read_text(encoding="utf-8"))
INVENTORY = json.loads((ARTIFACTS / "rbt002_input_coverage_inventory_v1.json").read_text(encoding="utf-8"))
WARM_UP = utc(2023, 6, 1)
DAYS = (utc(2024, 4, 7), utc(2024, 4, 8), utc(2024, 4, 9))


@pytest.fixture(scope="module")
def inputs():
    return Scenario().build()


@pytest.fixture(scope="module")
def ledger(inputs):
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    with recording("detect_bullish_reset") as calls:
        for instant in (WARM_UP, *DAYS):
            composer.record(composer.decide(instant))
        composer.record(composer.decide(utc(2024, 4, 10), position_open=True))
        composer.record(composer.decide(utc(2024, 4, 11)))
    return {"composer": composer, "rows": composer.ledger, "reset_calls": calls["detect_bullish_reset"]}


# --- the ledger row ------------------------------------------------------------------------


def test_each_decision_writes_exactly_one_row_with_an_outcome(ledger):
    rows = ledger["rows"]
    assert [row.decision_at for row in rows] == [WARM_UP, *DAYS, utc(2024, 4, 10), utc(2024, 4, 11)]
    for row in rows:
        assert row.outcome in OUTCOMES and row.reasons
        assert row.venue == "BITSTAMP"
        assert set(row.features) == set(FEATURE_NAMES)
        assert row.unaccounted == ()
    warm_up = rows[0]
    assert warm_up.outcome == OUTCOME_STRUCTURALLY_UNEVALUABLE
    assert {item.component for item in warm_up.unevaluable} == {"flow", "positioning"}
    assert all(item.causes for item in warm_up.unevaluable)
    assert [f"{item.component.upper()}_INCOMPLETE" for item in warm_up.unevaluable] == list(warm_up.reasons)


def test_nothing_is_zero_filled(ledger):
    warm_up = ledger["rows"][0]
    record = warm_up.as_record()
    assert record["components"]["flow"] is None and record["components"]["positioning"] is None
    assert record["entry_conviction"] is None and record["entry_action"] is None
    for name, value in warm_up.features.items():
        assert (record["features"][name] is None) == (value is None)
    missing = [name for name, value in warm_up.features.items() if value is None]
    assert {"FLOW_SCORE", "POSITIONING_SCORE", "ETF_NORM_5D", "FUNDING_HEALTH"} <= set(missing)
    # Decimals serialise exactly, never as a float
    assert record["components"]["trend"] == format(warm_up.components["trend"], "f")


def test_each_unevaluable_cause_carries_its_accounting(ledger):
    for item in ledger["rows"][0].unevaluable:
        record = item.as_record()
        for cause in record["causes"]:
            assert cause["accounted"] is not None, cause
            assert cause["accounted"] == accounted_cause(cause["code"]).as_record()


def test_owner_reason_codes_are_recorded_per_owner(ledger):
    row = ledger["rows"][3]
    codes = row.owner_reason_codes
    for label in ("funding_health", "futures_basis_health", "open_interest_growth_health", "flow_score", "volatility_score",
                  "regime_score", "regime_smoothing", "entry_conviction", "stress", "crowding", "clusters",
                  "stop:BULL_TREND_CONTINUATION", "setup:BEARISH_DISTRIBUTION"):
        assert set(codes[label]) == {"feature_id", "complete", "reason_codes"}, label
    assert "etf_anchor" not in codes  # its window value is never consumed


# --- determinism and serialisation -----------------------------------------------------------


def test_the_ledger_is_canonical_and_deterministic(ledger, inputs):
    composer = ledger["composer"]
    data = composer.ledger_bytes()
    parsed = json.loads(data)
    assert data == canonical_json_bytes(parsed)
    assert parsed["ledger_version"] == entry_composer.LEDGER_VERSION
    assert parsed["completion_spec"] == {"version": "CHAMPION_COMPLETION_SPEC_V1", "sha256": COMPLETION_SPEC_SHA256}
    assert parsed["closure_table"] == "US_EQUITY_MARKET_CLOSURE_TABLE_V1"
    assert composer.ledger_sha256() == hashlib.sha256(data).hexdigest()
    twin = EntryComposer(Scenario().build(), strategy_config=CONFIG)
    for instant in (WARM_UP, *DAYS):
        twin.record(twin.decide(instant))
    twin.record(twin.decide(utc(2024, 4, 10), position_open=True))
    twin.record(twin.decide(utc(2024, 4, 11)))
    assert twin.ledger_bytes() == data
    assert "ledger_json" in dir(entry_composer) and json.loads(entry_composer.ledger_json(composer)) == parsed


RUNNER = """
import sys
from btc_predictor.tests.rbt004_composer_fixtures import Scenario, utc
composer = Scenario().composer()
for instant in (utc(2023, 6, 1), utc(2024, 4, 9)):
    composer.record(composer.decide(instant))
print(composer.ledger_sha256())
"""


def test_the_ledger_digest_is_stable_across_hash_seeds_and_working_directories(tmp_path):
    script = tmp_path / "runner.py"
    script.write_text(RUNNER, encoding="utf-8")
    digests = set()
    for seed in ("0", "1", "8675309"):
        environment = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)}
        result = subprocess.run([sys.executable, str(script)], cwd=tmp_path, env=environment, capture_output=True, text=True, check=True, timeout=600)
        digests.add(result.stdout.strip())
    composer = Scenario().composer()
    for instant in (WARM_UP, utc(2024, 4, 9)):
        composer.record(composer.decide(instant))
    assert digests == {composer.ledger_sha256()}


# --- the decision API and the engine adapter ----------------------------------------------------


def test_decide_refuses_non_decision_instants_and_reordering(inputs):
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    with pytest.raises(EntryComposerError) as refused:
        composer.decide(utc(2024, 4, 9, 1))
    assert refused.value.code == "NOT_A_DECISION_INSTANT"
    with pytest.raises(EntryComposerError):
        composer.decide(datetime(2024, 4, 9))  # naive
    decision = composer.decide(utc(2024, 4, 9))
    assert composer.ledger == ()  # decide never writes
    composer.record(decision)
    for instant in (utc(2024, 4, 9), utc(2024, 4, 8)):
        with pytest.raises(EntryComposerError) as refused:
            composer.decide(instant)
        assert refused.value.code == "DECISION_ORDER"
    with pytest.raises(EntryComposerError):
        composer.record(decision)


def _engine_bars(inputs, start, end, *, drop=()):
    return tuple(bar for bar in inputs.dataset.price_bars if start <= bar.timestamp < end and bar.timestamp not in drop)


def test_the_engine_adapter_decides_at_midnights_only(inputs):
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    bars = _engine_bars(inputs, utc(2024, 4, 7, 20), utc(2024, 4, 9, 6))
    calls = []
    original = composer.decide

    def counting(instant, **kwargs):
        calls.append(instant)
        return original(instant, **kwargs)

    composer.decide = counting
    run_backtest(bars, strategy=composer, strategy_config=CONFIG, symbol=bars[0].symbol)
    midnights = [bar.ingested_at for bar in bars if bar.ingested_at.hour == 0]
    assert calls == midnights == [utc(2024, 4, 8), utc(2024, 4, 9)]
    assert [row.decision_at for row in composer.ledger] == midnights


def test_a_missed_midnight_is_backfilled_as_unevaluable(inputs):
    missing = utc(2024, 4, 8, 23)
    gapped = Scenario(missing_hours=(missing,)).build()
    composer = EntryComposer(gapped, strategy_config=CONFIG)
    bars = _engine_bars(gapped, utc(2024, 4, 7, 20), utc(2024, 4, 10, 2))
    result = run_backtest(bars, strategy=composer, strategy_config=CONFIG, symbol=bars[0].symbol)
    rows = composer.ledger
    assert [row.decision_at for row in rows] == [utc(2024, 4, 8), utc(2024, 4, 9), utc(2024, 4, 10)]
    skipped = rows[1]
    assert skipped.outcome == OUTCOME_STRUCTURALLY_UNEVALUABLE
    assert skipped.reasons == (CAUSE_DECISION_PRICE_BAR_MISSING,)
    assert skipped.unevaluable[0].component == "decision_instant"
    assert accounted_cause(CAUSE_DECISION_PRICE_BAR_MISSING).authority == AUTHORITY_INVENTORY_ROW
    assert skipped.position_open is False and skipped.intent is None and skipped.unaccounted == ()
    # the ledger schema is uniform: the skipped row has every key, all unevaluated
    assert set(skipped.regime) == set(rows[0].regime) and set(skipped.components) == set(rows[0].components)
    assert all(value is None for value in skipped.components.values()) and skipped.regime["smoothed_score"] is None
    assert set(skipped.as_record()) == set(rows[0].as_record())
    # the regime chain re-seeds after the gap (the owner's own missing-previous handling)
    assert rows[2].regime["previous_smoothed_score"] is None
    assert result.bar_count == len(bars)


def test_an_engine_that_skips_a_visible_decision_bar_is_a_composer_defect(inputs):
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    # The engine's bars omit the 23:00 bar the composer's replay inputs contain.
    bars = _engine_bars(inputs, utc(2024, 4, 7, 20), utc(2024, 4, 10, 2), drop=(utc(2024, 4, 8, 23),))
    with pytest.raises(EntryComposerError) as refused:
        run_backtest(bars, strategy=composer, strategy_config=CONFIG, symbol=bars[0].symbol)
    assert refused.value.code == "COMPOSER_DEFECT"
    assert [row.decision_at for row in composer.ledger] == [utc(2024, 4, 8)]


def test_the_composer_reads_its_own_replay_inputs_not_the_engine_prefix(inputs):
    long_run = EntryComposer(inputs, strategy_config=CONFIG)
    run_backtest(_engine_bars(inputs, utc(2024, 4, 7, 20), utc(2024, 4, 9, 1)), strategy=long_run, strategy_config=CONFIG, symbol=inputs.dataset.price_bars[0].symbol)
    short_run = EntryComposer(inputs, strategy_config=CONFIG)
    run_backtest(_engine_bars(inputs, utc(2024, 4, 8, 23), utc(2024, 4, 9, 1)), strategy=short_run, strategy_config=CONFIG, symbol=inputs.dataset.price_bars[0].symbol)
    long_row, short_row = long_run.ledger[-1], short_run.ledger[-1]
    assert long_row.decision_at == short_row.decision_at == utc(2024, 4, 9)
    # every input-derived value is identical; only the ledger-chained regime differs
    assert long_row.features | {"REGIME_SMOOTHED_SCORE": None} == short_row.features | {"REGIME_SMOOTHED_SCORE": None}
    assert long_row.components == short_row.components and long_row.flags == short_row.flags


# --- the runtime completeness guard and its accounting (policy V7 section 5A.6) -------------------


def _inventory_rows():
    rows: dict[str, list[dict]] = {}
    for row in INVENTORY["input_surface"]["rows"]:
        rows.setdefault(f"{row['owner']}.{row['name']}", []).append(row)
    return rows


def test_every_accounted_cause_is_backed_by_a_bound_artifact():
    entries = {entry["input_id"]: entry for entry in SPEC["entries"]}
    guards = {guard["guard_id"] for guard in SPEC["positioning_zero_variance_guards"]}
    minimum = {item["input_id"] for item in INVENTORY["minimum_history"]}
    rows = _inventory_rows()
    assert len(CAUSE_ACCOUNTING) > 100
    for key, cause in CAUSE_ACCOUNTING.items():
        if cause.authority == AUTHORITY_SPEC_ENTRY:
            assert cause.cause in entries[cause.reference]["accounted_causes"], key
        elif cause.authority == AUTHORITY_SPEC_GUARD:
            assert cause.reference in guards, key
        elif cause.authority == AUTHORITY_INVENTORY_ROW:
            assert any(cause.cause in (row.get("missing_behaviour") or "") for row in rows[cause.reference]), key
        else:
            assert cause.authority == AUTHORITY_INVENTORY_MINIMUM_HISTORY and cause.reference in minimum, key
    # the composer's bound spec is the persisted one
    persisted = (ARTIFACTS / completion_spec.SPEC_DIGEST_FILENAME).read_text(encoding="utf-8").split()[0]
    assert COMPLETION_SPEC_SHA256 == persisted == hashlib.sha256((ARTIFACTS / completion_spec.SPEC_FILENAME).read_bytes()).hexdigest()
    assert SPEC["bound_inventory"]["sha256"] == hashlib.sha256((ARTIFACTS / "rbt002_input_coverage_inventory_v1.json").read_bytes()).hexdigest()


def test_every_spec_cause_the_entry_composer_emits_is_accounted():
    entry_inputs = {
        "TREND_Z_M4", "TREND_Z_M12", "TREND_Z_20W", "TREND_Z_52H", "FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL",
        "RANGE_PERCENTILE", "DOWNSIDE_RETURN", "UPSIDE_RETURN", "LEVEL_REACTION_MAGNITUDE", "LEVEL_VOLUME_PERCENTILE",
        "SEVERE_CROWDING_STATE", "CORRECTION_FROM_LOCAL_HIGH", "MEASURED_MOVE_REFERENCE",
    }
    for entry in SPEC["entries"]:
        if entry["input_id"] in entry_inputs:
            for cause in entry["accounted_causes"]:
                assert accounted_cause(cause) is not None, cause


def test_an_unaccounted_owner_code_is_reported(inputs, monkeypatch):
    real = entry_composer.calculate_orderliness_score

    def with_unknown_code(*args, **kwargs):
        result = real(*args, **kwargs)
        return replace(result, reason_codes=(*result.reason_codes, "SYNTHETIC_FEED_INPUT_MISSING"))

    monkeypatch.setattr(entry_composer, "calculate_orderliness_score", with_unknown_code)
    row = EntryComposer(inputs, strategy_config=CONFIG).decide(utc(2024, 4, 9)).row
    assert row.unaccounted == ("orderliness:SYNTHETIC_FEED_INPUT_MISSING",)


def test_an_incomplete_result_with_no_accounted_code_is_reported(inputs, monkeypatch):
    real = entry_composer.calculate_crowding_flag

    def incomplete(*args, **kwargs):
        result = real(*args, **kwargs)
        return replace(result, complete=False, reason_codes=("SYNTHETIC_UNKNOWN_STATE",))

    monkeypatch.setattr(entry_composer, "calculate_crowding_flag", incomplete)
    row = EntryComposer(inputs, strategy_config=CONFIG).decide(utc(2024, 4, 9)).row
    assert "crowding:SYNTHETIC_UNKNOWN_STATE" in row.unaccounted


def test_composer_unaccounted_causes_are_collected(ledger):
    assert ledger["composer"].unaccounted_causes() == ()


# --- inputs and identity ------------------------------------------------------------------------


def test_the_composer_refuses_a_non_champion_identity(inputs):
    other = replace(CONFIG, identity=replace(CONFIG.identity, parameter_set_id="research_variant"))
    with pytest.raises(EntryComposerError) as refused:
        EntryComposer(inputs, strategy_config=other)
    assert refused.value.code == "CHAMPION_IDENTITY"
    with pytest.raises(EntryComposerError):
        EntryComposer(inputs, strategy_config=object())  # type: ignore[arg-type]
    with pytest.raises(EntryComposerError):
        EntryComposer(object(), strategy_config=CONFIG)  # type: ignore[arg-type]
    assert dict(CONFIG.run_metadata()) == dict(completion_spec.CHAMPION_BASE_IDENTITY)
    assert load_strategy_config().run_metadata() == CONFIG.run_metadata()


def test_composer_inputs_are_validated(inputs):
    with pytest.raises(EntryComposerError):
        EntryComposerInputs(dataset=object())  # type: ignore[arg-type]
    day = date(2024, 4, 8)
    good = LiquidationPercentileObservation(day, Decimal("40"), utc(2024, 4, 9))
    with pytest.raises(EntryComposerError):
        with_inputs(inputs, liquidation_percentiles=(good, good))
    with pytest.raises(EntryComposerError):
        LiquidationPercentileObservation(day, Decimal("40"), utc(2024, 4, 8, 23))  # available before the day ends
    with pytest.raises(EntryComposerError):
        LiquidationPercentileObservation(day, Decimal("101"), utc(2024, 4, 9))
    with pytest.raises(EntryComposerError):
        LiquidationPercentileObservation(day, 40.0, utc(2024, 4, 9))  # type: ignore[arg-type]
    unordered = replace(inputs.dataset, price_bars=tuple(replace(bar, ingested_at=bar.ingested_at - 2 * HOUR) if index == 5 else bar for index, bar in enumerate(inputs.dataset.price_bars)))
    with pytest.raises(EntryComposerError) as refused:
        EntryComposer(with_inputs(inputs, dataset=unordered), strategy_config=CONFIG)
    assert "nondecreasing" in str(refused.value)


def test_a_missing_liquidation_percentile_leaves_orderliness_incomplete(inputs):
    instant = utc(2024, 4, 9)
    without = EntryComposer(with_inputs(inputs, liquidation_percentiles=()), strategy_config=CONFIG).decide(instant).row
    refused_day = tuple(
        replace(item, liquidation_percentile=None, reason_codes=("LIQUIDATION_FEED_UNAVAILABLE",)) if item.observation_date == date(2024, 4, 8) else item
        for item in inputs.liquidation_percentiles
    )
    refused = EntryComposer(with_inputs(inputs, liquidation_percentiles=refused_day), strategy_config=CONFIG).decide(instant).row
    # the last completed day has no row: an older day is never substituted (no forward fill)
    gap = tuple(item for item in inputs.liquidation_percentiles if item.observation_date != date(2024, 4, 8))
    stale = EntryComposer(with_inputs(inputs, liquidation_percentiles=gap), strategy_config=CONFIG).decide(instant).row
    assert any(item.observation_date == date(2024, 4, 7) for item in gap)
    for row in (without, refused, stale):
        assert row.outcome == OUTCOME_STRUCTURALLY_UNEVALUABLE and "VOLATILITY_INCOMPLETE" in row.reasons
        volatility = {item.component: item.causes for item in row.unevaluable}["volatility"]
        assert CAUSE_LIQUIDATION_PERCENTILE_MISSING in volatility and "ORDERLINESS_INPUT_MISSING" in volatility
        assert row.features["ORDERLINESS_SCORE"] is None
        assert row.flags["stress"]["mapped"] is None  # STRESS_NON_DISCRETIONARY_MISSING
        assert row.unaccounted == ()
    cause = accounted_cause(CAUSE_LIQUIDATION_PERCENTILE_MISSING)
    assert cause.reference == "btc_predictor.features.volatility.OrderlinessScoreInput.liquidation_percentile"
    # the consumed observation is the UTC day ending at t, available exactly at t
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    run = _DecisionRun(composer, instant, position_open=False)
    assert run._liquidation_percentile() == next(item.liquidation_percentile for item in inputs.liquidation_percentiles if item.observation_date == date(2024, 4, 8))


# --- the regime chain and the open position ------------------------------------------------------


def test_regime_smoothing_chains_from_the_previous_ledger_row(ledger):
    rows = ledger["rows"]
    # At warm-up the core regime itself is incomplete (flow is a core component),
    # so there is no smoothed score to chain from; the next row seeds the chain.
    warm_up, seed = rows[0], rows[1]
    assert warm_up.regime["score"] is None and warm_up.regime["smoothed_score"] is None
    assert warm_up.owner_reason_codes["regime_smoothing"]["reason_codes"] == ["REGIME_SMOOTHING_NEW_SCORE_MISSING"]
    assert seed.regime["previous_smoothed_score"] is None and seed.regime["smoothed_score"] == seed.regime["score"]
    assert "REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING" in seed.owner_reason_codes["regime_smoothing"]["reason_codes"]
    for previous, row in zip(rows[1:], rows[2:]):
        assert row.regime["previous_smoothed_score"] == previous.regime["smoothed_score"]
        expected = calculate_regime_smoothing(
            RegimeSmoothingInput(previous_smoothed_score=previous.regime["smoothed_score"], new_regime_score=row.regime["score"]),
            previous_weight=CONFIG.regime_smoothing.previous_weight,
            new_weight=CONFIG.regime_smoothing.new_weight,
        )
        assert row.regime["smoothed_score"] == expected.score
        assert row.regime["classification"] is not None and row.features["REGIME_SMOOTHED_SCORE"] == expected.score
    # macro and on-chain are declared unavailable: the Rulebook core regime fallback
    assert {row.regime["model"] for row in rows[1:]} == {REGIME_MODEL_CORE_MARKET_ONLY}


def test_an_open_position_records_no_trade_and_keeps_the_chain(ledger):
    open_row, after = ledger["rows"][4], ledger["rows"][5]
    assert open_row.outcome == OUTCOME_NO_TRADE and open_row.reasons == (REASON_POSITION_ALREADY_OPEN,)
    assert open_row.position_open is True and open_row.intent is None and open_row.detected_setups == ()
    assert open_row.regime["smoothed_score"] is not None and open_row.entry_conviction is not None
    assert after.regime["previous_smoothed_score"] == open_row.regime["smoothed_score"]


def test_setup_b_oi_health_history_uses_prior_daily_instants(ledger, inputs):
    shared = inputs.dataset.shared_snapshot
    lookback = int(CONFIG.setup_requirements.bullish_reset["oi_health_stable_days"])
    call = next(call for call in ledger["reset_calls"] if call.result is not None and len(call.args[0].oi_health_history) == lookback + 1)
    history = call.args[0].oi_health_history
    first = [row for row in ledger["rows"] if row.owner_reason_codes.get("setup:BULLISH_RESET")][0].decision_at
    expected = tuple(
        positioning_owner.open_interest_growth_health(
            tuple(row for row in shared.open_interest if row.available_at <= first - days_back * DAY), as_of=first - days_back * DAY, open_interest_unit="USD"
        ).health_score
        for days_back in range(lookback, -1, -1)
    )
    assert tuple(history) == expected


# --- the CAPITULATION episode (owner ruling: 14-day memory, first instant of the run) ---------------


@pytest.fixture(scope="module")
def episode_composer(inputs):
    return EntryComposer(inputs, strategy_config=CONFIG)


def _rows_ending_before(template, states, t):
    """Ledger rows at the daily instants just before ``t``, oldest first, with these flag states."""

    return [replace(template, decision_at=t - (len(states) - index) * DAY, capitulation_flag_state=state) for index, state in enumerate(states)]


# (prior daily states oldest first, state at t, expected flag, expected start as days before t)
EPISODES = {
    "a fully known unflagged window": ([False] * 14, False, False, None),
    "a window instant with no ledger row is unknown, never False": ([False] * 13, False, None, None),
    "an unknown state in the window": ([None] + [False] * 13, False, None, None),
    "the first instant of the flagged run": ([False] * 11 + [True] * 3, False, True, 3),
    "flagged at t": ([False] * 14, True, True, 0),
    "a run that began before the window": ([False] * 2 + [True] * 8 + [False] * 10, False, True, 18),
    "the latest flag is outside the window": ([True] * 2 + [False] * 18, False, False, None),
    "a flag exactly 14 days back counts": ([False] * 5 + [True] + [False] * 13, False, True, 14),
    "an unknown predecessor leaves the start undetermined": ([None] + [True] * 3 + [False] * 10, False, True, None),
    "a run reaching the ledger start has no determined start": ([True] * 3 + [False] * 11, False, True, None),
}


@pytest.mark.parametrize("name", sorted(EPISODES))
def test_the_capitulation_episode(name, ledger, episode_composer):
    states, now, expected_flag, start_days = EPISODES[name]
    t = utc(2024, 6, 1)
    episode_composer._ledger[:] = _rows_ending_before(ledger["rows"][3], states, t)
    run = _DecisionRun(episode_composer, t, position_open=False)
    run.capitulation_now = now
    flag, start = run._capitulation_episode()
    assert int(CONFIG.setup_requirements.capitulation_reversal["max_confirmation_lag_days"]) == 14
    assert flag is expected_flag
    assert start == (None if start_days is None else t - start_days * DAY)
