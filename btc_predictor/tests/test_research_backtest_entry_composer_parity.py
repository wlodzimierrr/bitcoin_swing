"""RBT-004: batch/single parity with the BTC-048 point-in-time feature matrix.

The composer's ledger carries the BTC-048 ``INITIAL_FEATURE_NAMES`` columns.
Three parities are proven on the same synthetic inputs:

- the matrix built from the composer's per-instant values reproduces them
  exactly (float64, a missing value stays missing);
- every single-owner feature equals a direct owner call on the same
  point-in-time inputs, recomputed here independently;
- the batch Entry Conviction owner over the matrix's component columns equals
  each row's single Entry Conviction.

Importing ``btc_predictor.research`` in a test is allowed; only production
EPIC Y modules are barred from BTC-019 research modules.
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pytest

from btc_predictor.features.entry import calculate_entry_conviction_batch
from btc_predictor.features.flow import etf_flow_acceleration, five_day_etf_flow, twenty_day_etf_flow
from btc_predictor.features.momentum import four_week_momentum_from_daily_bars, twelve_week_momentum_from_daily_bars
from btc_predictor.features.positioning import funding_health, futures_basis_health, open_interest_growth_health, open_interest_intensity
from btc_predictor.features.trend import fifty_two_week_high_distance_from_weekly_bars, twenty_week_ma_distance_from_weekly_bars
from btc_predictor.features.volatility import realized_volatility_from_daily_bars, volatility_compression_ratio_from_results, volatility_percentile
from btc_predictor.research.feature_matrix import INITIAL_FEATURE_NAMES, FeatureObservation, build_point_in_time_feature_matrix
from btc_predictor.research.us_equity_market_closures import COVERAGE_END, COVERAGE_START, load_closures
from btc_predictor.research_backtest.entry_composer import FEATURE_NAMES, EntryComposer
from btc_predictor.research_backtest.replay_inputs import replay_market_bars_at
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, DEFAULT_FUNDS, Scenario, us_trading_days, utc

INSTANTS = (utc(2023, 6, 1), utc(2023, 11, 1), *(utc(2024, 4, 1) + offset * DAY for offset in range(9)))
COMPONENTS = ("TREND_SCORE", "FLOW_SCORE", "POSITIONING_SCORE", "VOLATILITY_SCORE", "STRUCTURE_SCORE")
TABLE = load_closures(COVERAGE_START, COVERAGE_END)
LAUNCHES = {spec.fund: spec.launch for spec in DEFAULT_FUNDS}


@pytest.fixture(scope="module")
def run():
    inputs = Scenario().build()
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    rows = []
    for instant in INSTANTS:
        decision = composer.decide(instant)
        composer.record(decision)
        rows.append(decision.row)
    return {"inputs": inputs, "composer": composer, "rows": rows}


@pytest.fixture(scope="module")
def matrix(run):
    observations = [
        FeatureObservation(name, row.features[name], row.decision_at, row.decision_at, f"rbt004:{row.decision_at.isoformat()}")
        for row in run["rows"]
        for name in FEATURE_NAMES
    ]
    return build_point_in_time_feature_matrix(observations, [row.decision_at for row in run["rows"]])


def test_the_ledger_carries_the_btc048_columns_in_order():
    assert FEATURE_NAMES == INITIAL_FEATURE_NAMES


def test_the_matrix_reproduces_every_composer_value(run, matrix):
    values = matrix.to_numpy()
    complete_cells = 0
    for row_index, row in enumerate(run["rows"]):
        for column, name in enumerate(INITIAL_FEATURE_NAMES):
            value = row.features[name]
            if value is None:
                assert matrix.missing_mask[row_index, column], (row.decision_at, name)
            else:
                assert not matrix.missing_mask[row_index, column]
                assert values[row_index, column] == float(value), (row.decision_at, name)
                complete_cells += 1
    assert complete_cells > 200
    # warm-up rows really are partially missing, and CVD never exists (ETF_CORE)
    assert matrix.missing_mask[0, INITIAL_FEATURE_NAMES.index("FLOW_SCORE")]
    assert matrix.missing_mask[:, INITIAL_FEATURE_NAMES.index("CVD_SPREAD")].all()


def test_batch_entry_conviction_equals_each_single_score(run, matrix):
    columns = [INITIAL_FEATURE_NAMES.index(name) for name in COMPONENTS]
    batch = calculate_entry_conviction_batch(matrix.to_numpy()[:, columns], strategy_config=CONFIG)
    scores = np.asarray(batch.scores, dtype=np.float64).reshape(-1)
    evaluated = 0
    for index, row in enumerate(run["rows"]):
        if row.entry_conviction is None:
            assert math.isnan(scores[index]), row.decision_at
        else:
            assert scores[index] == pytest.approx(float(row.entry_conviction), rel=1e-12, abs=1e-12), row.decision_at
            evaluated += 1
    assert evaluated >= 5


# --- independent single-owner recomputation ------------------------------------------------------


def _bars(inputs, instant):
    hourly = tuple(sorted((bar for bar in inputs.dataset.price_bars if bar.ingested_at <= instant), key=lambda bar: bar.timestamp))
    canonical = replay_market_bars_at(hourly, decision_at=instant, window=inputs.dataset.window)
    return tuple(bar for bar in canonical if bar.timeframe == "1d"), tuple(bar for bar in canonical if bar.timeframe == "1w")


def _independent_features(inputs, instant):
    daily, weekly = _bars(inputs, instant)
    shared = inputs.dataset.shared_snapshot
    rv = {window: realized_volatility_from_daily_bars(daily, as_of=instant, window_days=window) for window in (7, 20, 60)}
    # the RV_20 history over every prior daily bar (a superset of the owner's own 730-day window)
    history = [realized_volatility_from_daily_bars(daily, as_of=bar.ingested_at, window_days=20) for bar in daily[:-1]]
    percentile = volatility_percentile((*history, rv[20]), as_of=instant)
    funding = funding_health(tuple(row for row in shared.funding_rates if row.available_at <= instant), as_of=instant)
    oi_rows = tuple(row for row in shared.open_interest if row.available_at <= instant)
    growth = open_interest_growth_health(oi_rows, as_of=instant, open_interest_unit="USD")
    caps = tuple(cap for cap in inputs.market_caps if cap.available_at <= instant)
    intensity = open_interest_intensity(oi_rows, caps, as_of=instant, open_interest_unit="USD")
    basis = futures_basis_health(tuple(row for row in inputs.futures_basis if row.available_at <= instant), as_of=instant)
    values = {
        "RV_7": rv[7].realized_volatility,
        "RV_20": rv[20].realized_volatility,
        "RV_60": rv[60].realized_volatility,
        "VOL_PERCENTILE_2Y": percentile.volatility_percentile,
        "VOL_COMPRESSION_RATIO": volatility_compression_ratio_from_results((rv[7], rv[60])).compression_ratio,
        "MOMENTUM_4W": four_week_momentum_from_daily_bars(daily)[-1],
        "MOMENTUM_12W": twelve_week_momentum_from_daily_bars(daily)[-1],
        "MA_DISTANCE_20W": twenty_week_ma_distance_from_weekly_bars(weekly)[-1],
        "HIGH_DISTANCE_52W": fifty_two_week_high_distance_from_weekly_bars(weekly)[-1],
        "FUNDING_7D_AVG": funding.funding_7d_avg,
        "FUNDING_ZSCORE_180D": funding.funding_zscore,
        "FUNDING_HEALTH": funding.health_score,
        "OI_GROWTH_7D": growth.oi_growth,
        "OI_GROWTH_ZSCORE_180D": growth.oi_growth_zscore,
        "OI_GROWTH_HEALTH": growth.health_score,
        "OI_INTENSITY": intensity.oi_intensity,
        "OI_INTENSITY_PERCENTILE_180D": intensity.oi_intensity_percentile,
        "FUTURES_BASIS_AVG": basis.annualized_basis_rate_avg,
        "FUTURES_BASIS_ZSCORE_180D": basis.annualized_basis_zscore,
        "FUTURES_BASIS_HEALTH": basis.health_score,
        "CVD_SPREAD": None,
        "SPOT_DOMINANCE": None,
    }
    visible = tuple(flow for flow in shared.etf_flows if flow.available_at <= instant)
    if visible:
        latest = max(flow.observation_date for flow in visible)
        days = list(reversed(us_trading_days(date(2023, 12, 1), latest)))
        windows = {}
        for size, owner in ((5, five_day_etf_flow), (20, twenty_day_etf_flow)):
            funds = tuple(sorted(fund for fund, launch in LAUNCHES.items() if launch <= days[size - 1]))
            windows[size] = owner(visible, as_of=instant, funds=funds, market_holidays=TABLE, end_date=latest) if funds else None
        values["ETF_NORM_5D"] = windows[5].normalized_flow if windows[5] is not None and windows[5].complete else None
        values["ETF_NORM_20D"] = windows[20].normalized_flow if windows[20] is not None and windows[20].complete else None
        accel = etf_flow_acceleration(windows[5], windows[20]) if windows[5] is not None and windows[20] is not None else None
        values["FLOW_ACCEL"] = accel.acceleration if accel is not None and accel.complete else None
    else:
        values.update({"ETF_NORM_5D": None, "ETF_NORM_20D": None, "FLOW_ACCEL": None})
    return values


@pytest.mark.parametrize("instant", [utc(2023, 11, 1), utc(2024, 4, 9)])
def test_single_owner_features_equal_direct_owner_calls(run, instant):
    row = next(row for row in run["rows"] if row.decision_at == instant)
    expected = _independent_features(run["inputs"], instant)
    assert len(expected) == 25
    for name, value in expected.items():
        assert row.features[name] == value, (instant, name)
    if instant == utc(2024, 4, 9):
        assert all(row.features[name] is not None for name in expected if name not in ("CVD_SPREAD", "SPOT_DOMINANCE"))


def test_features_are_identical_for_an_independently_built_composer(run):
    twin = EntryComposer(Scenario().build(), strategy_config=CONFIG)
    for instant, row in zip(INSTANTS[-2:], run["rows"][-2:]):
        features = twin.decide(instant).row.features
        # only the ledger-chained smoothed regime depends on the earlier rows
        assert {**features, "REGIME_SMOOTHED_SCORE": None} == {**row.features, "REGIME_SMOOTHED_SCORE": None}
