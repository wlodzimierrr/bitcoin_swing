"""Offline RBT-002A review witnesses: inventory dates and synthetic values only.

Run with .venv312/bin/python. No database, environment files, market values or
backtest outcomes are used. Calendar bucketing and warm-up are independent of
completion_spec's simulation and coverage's bar/series builders.
"""

from bisect import bisect_left
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import hashlib
import inspect
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from btc_predictor.features import flow, positioning
from btc_predictor.research_backtest import completion_spec as spec
from btc_predictor.research.us_equity_market_closures import load_closures

DAY = timedelta(days=1)
HOUR = timedelta(hours=1)
START = datetime(2020, 1, 1, tzinfo=UTC)
END = datetime(2026, 1, 1, tzinfo=UTC)


def _missing(entry):
    result = set()
    for first, last, count in entry["data_window"]["missing_runs"]:
        a, b = datetime.fromisoformat(first), datetime.fromisoformat(last)
        points = {a + i * HOUR for i in range(count)}
        assert max(points) == b
        result.update(points)
    return result


def _buckets(missing, timeframe):
    current = START
    if timeframe == "1w":
        current += timedelta(days=(7 - current.weekday()) % 7)
    result = []
    while current < END:
        if timeframe == "1mo":
            following = current.replace(year=current.year + (current.month == 12), month=current.month % 12 + 1)
        else:
            following = current + (DAY if timeframe == "1d" else 7 * DAY)
        if following <= END and not any(current <= hour < following for hour in missing):
            result.append((current, following))
        current = following
    return result


def _first_z(base, count_window):
    if count_window:
        return base[20][1]
    for index, (current, available) in enumerate(base):
        count = sum(current - 730 * DAY <= time < current for time, _ in base[:index])
        if count >= 30:
            return available
    raise AssertionError("no normalization warm-up")


def _volume_pivots(bars, missing, right_bars):
    missing = sorted(missing)

    def defined(close, length):
        start = close - length
        index = bisect_left(missing, start)
        return start >= START and close <= END and (index == len(missing) or missing[index] >= close)

    for index, (start, close) in enumerate(bars):
        length = close - start
        count = sum(defined(close - offset * DAY, length) for offset in range(1, 731))
        if defined(close, length) and count >= 365:
            return close, bars[index + right_bars][1], count
    raise AssertionError("no volume warm-up")


def review_witness():
    directory = ROOT / "backtest_evidence/research_backtest_v1"
    raw = (directory / "rbt002_input_coverage_inventory_v1.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == spec.BOUND_INVENTORY_SHA256
    inventory = json.loads(raw)
    definition = json.loads((directory / spec.SPEC_FILENAME).read_bytes())
    entries = {item["input_id"]: item for item in definition["entries"]}
    count_window = any(item["rule_id"] == "UNIFORM_ZSCORE_V1" and
                       any(element["name"] == "window" and element["value"] == "20 prior defined native observations"
                           for element in item["elements"]) for item in definition["uniform_rules"])
    # Authorized closure-table dates are availability facts, not market data.
    holidays = load_closures(datetime(2023, 1, 1).date(), datetime(2026, 12, 31).date())
    publication = []
    current = datetime(2024, 1, 11, tzinfo=UTC)
    while current < END:
        if current.weekday() < 5 and current.date() not in holidays:
            publication.append((current, current + 2 * DAY))
        current += DAY
    all_series = inventory["database_coverage"]["raw_tables"]["raw.btc_ohlcv"]["series"]
    bitstamp = next(item for item in all_series if item["key"]["exchange"] == "bitstamp")
    shared_missing = _missing(bitstamp)
    pivots = {
        timeframe: _volume_pivots(_buckets(shared_missing, timeframe), shared_missing, right)
        for timeframe, right in [("1w", 3), ("1mo", 2)]
    }
    matrix = {}
    for venue in ("BITSTAMP", "COINBASE", "BITFINEX"):
        entry = next(item for item in all_series if item["key"]["exchange"] == venue.lower())
        missing = _missing(entry)
        daily, weekly = _buckets(missing, "1d"), _buckets(missing, "1w")
        native = {"TREND_Z_M4": daily[28:], "TREND_Z_M12": daily[84:],
                  "TREND_Z_20W": weekly[19:], "TREND_Z_52H": weekly[51:],
                  "FLOW_Z_ETF_NORM_5D": publication[4:], "FLOW_Z_ETF_NORM_20D": publication[19:],
                  "FLOW_Z_FLOW_ACCEL": publication[19:]}
        result = {key: _first_z(series, count_window) for key, series in native.items()}
        tr = [(time, available) for index, (time, available) in enumerate(daily)
              if index and daily[index - 1][0] == time - DAY]
        for index, (current, available) in enumerate(tr):
            if sum(current - 730 * DAY <= time < current for time, _ in tr[:index]) >= 365:
                result["RANGE_PERCENTILE"] = available
                break
        result.update({"DOWNSIDE_RETURN": daily[7][1], "UPSIDE_RETURN": daily[7][1],
                       "LEVEL_REACTION_MAGNITUDE": weekly[6][1],
                       "LEVEL_VOLUME_PERCENTILE": pivots["1w"][1],
                       "NEW_STRUCTURE_SCORE": max(weekly[6][1], pivots["1w"][1]),
                       "NEW_STRUCTURAL_CONFIRMATION": weekly[6][1],
                       "CORRECTION_FROM_LOCAL_HIGH": weekly[51][1],
                       "MOMENTUM_PERSISTENCE_SCORE": result["TREND_Z_M12"],
                       "ADD_MOMENTUM_SCORE": result["TREND_Z_M4"]})
        # These unchanged owner inputs already have bound inventory facts.
        facts = inventory["earliest_evaluable"]["venues"][venue]["inputs"]
        owner_dates = [datetime.fromisoformat(facts[key]["available_at"])
                       for key in ("POSITIONING_SCORE", "VOL_PERCENTILE_2Y", "LIQUIDATION_PERCENTILE")]
        lower_bound = max(*owner_dates, *(result[key] for key in native),
                          result["RANGE_PERCENTILE"], result["NEW_STRUCTURE_SCORE"])
        for key in ("REGIME_SUPPORTIVE_PREDICATE", "FLOW_SUPPORTIVE_PREDICATE", "REGIME_INVALIDATION_PREDICATE"):
            result[key] = lower_bound
        result["SEVERE_CROWDING_STATE"] = datetime.fromisoformat(facts["POSITIONING_SCORE"]["available_at"])
        for key, record in entries.items():
            if record["warm_up"]["kind"] == "NO_WARM_UP":
                result[key] = None
        assert set(result) == set(entries), (set(entries) - set(result), set(result) - set(entries))
        observed = definition["warm_up"]["by_venue"][venue]
        for key, time in result.items():
            assert (time.isoformat() if time else None) == observed["entries"][key].get("available_at"), (venue, key)
        assert lower_bound.isoformat() == ("2024-03-10T00:00:00+00:00" if count_window else "2024-03-24T00:00:00+00:00")
        assert definition["earliest_evaluable_effect"][venue]["spec_completed_status"] == "DATA_DEPENDENT_LOWER_BOUND"
        matrix[venue] = {key: time.isoformat() if time else None for key, time in sorted(result.items())}

    defaults = inspect.signature(flow.spot_perp_cvd_spread).parameters
    assert defaults["zscore_window_periods"].default == 20
    assert defaults["min_zscore_periods"].default is None  # owner resolves it to window
    synthetic = [Decimal(index) for index in range(1, 22)]
    owner_value = flow._latest_zscore(synthetic, window=20, min_periods=20)
    assert owner_value is not None
    assert max(i for i in range(100) if 7 * i <= 180) == 25
    return {
        "availability_matrix": matrix,
        "volume_pivots": {key: [close.isoformat(), detected.isoformat(), count]
                          for key, (close, detected, count) in pivots.items()},
        "source_precedence_counterexample": {
            "existing_owner": "btc_predictor.features.flow.spot_perp_cvd_spread",
            "existing_rule": "20 prior native observations, minimum 20, population, current excluded",
            "feasible_on_daily_weekly_and_publication_cadences": True,
            "synthetic_owner_result_complete": owner_value is not None,
            "positioning_180_day_weekly_capacity": 25,
            "finding": "Rejecting 180/30 as infeasible is sound. It does not authorize bypassing the feasible existing 20/20 z convention for NEW_PARAMETER 730/30 under V7 section 6A.2.",
        },
        "inventory_sha256": spec.BOUND_INVENTORY_SHA256,
        "spec_sha256": hashlib.sha256((directory / spec.SPEC_FILENAME).read_bytes()).hexdigest(),
        "data_used": "bound inventory availability facts, authorized closure dates, owner source, synthetic values only",
        "database_connected": False,
        "real_data_value_computed": False,
    }


if __name__ == "__main__":
    print(json.dumps(review_witness(), indent=2, sort_keys=True))
