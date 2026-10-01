"""Deterministic synthetic fixtures for the trend / momentum / Entry Conviction roots.

Group G1 of the RBT-002 runtime cross-check (policy V4 section 5A): each thunk
builds synthetic owner inputs from ``btc_predictor`` owner types and the stdlib
only, calls one decision-path root and returns that root's result, so that
``input_census.trace_owner_calls`` can compare what actually runs with the
static census.

Determinism: no randomness, no wall clock, no network, no database, no files
other than the champion strategy configuration, which is loaded once at import
time through ``btc_predictor.config.strategy.load_strategy_config()``. Loading
it at import time (outside every traced thunk) keeps the configuration parser
out of the traced call sets: it is fixture setup, not part of any root's
decision path. Every synthetic timestamp lies inside 2023-01-01..2024-12-31
and is timezone-aware UTC.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.data.ohlcv import OhlcvBar
from btc_predictor.features.entry import (
    EntryConvictionInput,
    calculate_entry_conviction,
    classify_entry_action,
)
from btc_predictor.features.momentum import (
    FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS,
    TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS,
    four_week_momentum_from_daily_bars,
    twelve_week_momentum_from_daily_bars,
)
from btc_predictor.features.trend import (
    DEFAULT_TREND_SCORE_WEIGHTS,
    FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS,
    TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS,
    TrendScoreInput,
    calculate_trend_score,
    classify_weekly_structure_from_weekly_bars,
    fifty_two_week_high_distance_from_weekly_bars,
    twenty_week_ma_distance_from_weekly_bars,
)


# --- champion configuration (loaded once, outside every traced thunk) --------------

CHAMPION_CONFIG: StrategyConfig = load_strategy_config()


# --- fixed synthetic calendar ------------------------------------------------------

# 2023-01-01 is a Sunday; daily bars open at 00:00 UTC.
DAILY_START = datetime(2023, 1, 1, tzinfo=UTC)
# 2023-01-02 is a Monday; canonical weekly bars open Monday 00:00 UTC.
WEEKLY_START = datetime(2023, 1, 2, tzinfo=UTC)
# One fixed ingestion instant after every synthetic bar.
INGESTED_AT = datetime(2024, 12, 30, tzinfo=UTC)

EXCHANGE = "coinbase"
SYMBOL = "BTC-USD"
PROVIDER = "coinbase"


def _bar(
    timestamp: datetime,
    timeframe: str,
    *,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange=EXCHANGE,
        symbol=SYMBOL,
        timeframe=timeframe,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=Decimal("125.5"),
        provider=PROVIDER,
        ingested_at=INGESTED_AT,
    )


def _daily_bars(count: int) -> tuple[OhlcvBar, ...]:
    """A deterministic rising-with-pullbacks daily close path from 2023-01-01."""

    bars = []
    for index in range(count):
        # +40 per day with a -150 pullback every seventh day (no zero/negative prices).
        close = Decimal(20000 + 40 * index - (150 if index % 7 == 6 else 0))
        open_ = close - Decimal("25")
        bars.append(
            _bar(
                DAILY_START + timedelta(days=index),
                "1d",
                open_=open_,
                high=close + Decimal("120"),
                low=open_ - Decimal("110"),
                close=close,
            )
        )
    return tuple(bars)


def _weekly_bars(count: int) -> tuple[OhlcvBar, ...]:
    """A deterministic weekly path from Monday 2023-01-02 (rise, drawdown, recovery)."""

    bars = []
    for index in range(count):
        if index < 30:
            close = Decimal(18000 + 400 * index)
        elif index < 42:
            close = Decimal(29600 - 350 * (index - 29))
        else:
            close = Decimal(25400 + 300 * (index - 41))
        open_ = close - Decimal("200")
        bars.append(
            _bar(
                WEEKLY_START + timedelta(weeks=index),
                "1w",
                open_=open_,
                high=close + Decimal("650"),
                low=open_ - Decimal("500"),
                close=close,
            )
        )
    return tuple(bars)


def _weekly_bars_from_ranges(ranges: tuple[tuple[str, str], ...]) -> tuple[OhlcvBar, ...]:
    """Weekly bars with explicit (high, low) ranges; open/close inside the range."""

    bars = []
    for index, (high_text, low_text) in enumerate(ranges):
        high = Decimal(high_text)
        low = Decimal(low_text)
        mid = (high + low) / Decimal("2")
        bars.append(
            _bar(
                WEEKLY_START + timedelta(weeks=index),
                "1w",
                open_=mid,
                high=high,
                low=low,
                close=mid,
            )
        )
    return tuple(bars)


# Every Rulebook 5.1 weekly structure label in sequence after the first week:
# HH_HL, HL_ONLY, MIXED (equal), LH_ONLY, LH_LL, MIXED (outside week).
ALL_LABEL_WEEKLY_RANGES: tuple[tuple[str, str], ...] = (
    ("30000", "27000"),
    ("31000", "28000"),
    ("30800", "28500"),
    ("30800", "28500"),
    ("30200", "28500"),
    ("29000", "27500"),
    ("29500", "27000"),
)


# --- calculate_entry_conviction ------------------------------------------------------


def entry_conviction_complete() -> object:
    """All five component scores present: COMPLETE with a score."""

    inputs = EntryConvictionInput(
        trend_score=Decimal("82.5"),
        flow_score=Decimal("71.0"),
        positioning_score=Decimal("64.0"),
        volatility_score=Decimal("58.0"),
        structure_score=Decimal("88.0"),
    )
    return calculate_entry_conviction(inputs, strategy_config=CHAMPION_CONFIG)


def entry_conviction_missing_component() -> object:
    """The flow component is unavailable: INPUT_MISSING, score None."""

    inputs = EntryConvictionInput(
        trend_score=Decimal("82.5"),
        flow_score=None,
        positioning_score=Decimal("64.0"),
        volatility_score=Decimal("58.0"),
        structure_score=Decimal("88.0"),
    )
    return calculate_entry_conviction(inputs, strategy_config=CHAMPION_CONFIG)


def entry_conviction_from_upstream_trend_owner() -> object:
    """Trend component produced by the trend owners (structure + trend score)."""

    structure = classify_weekly_structure_from_weekly_bars(
        _weekly_bars_from_ranges(ALL_LABEL_WEEKLY_RANGES[:2])
    )[-1]
    assert structure is not None
    trend = calculate_trend_score(
        TrendScoreInput(
            z_m4=Decimal("1.10"),
            z_m12=Decimal("0.85"),
            z_20w=Decimal("0.60"),
            structure_score=structure.raw_score,
            z_52h=Decimal("-0.25"),
        )
    )
    inputs = EntryConvictionInput(
        trend_score=trend.score,
        flow_score=Decimal("71.0"),
        positioning_score=Decimal("64.0"),
        volatility_score=Decimal("58.0"),
        structure_score=Decimal("88.0"),
    )
    return calculate_entry_conviction(inputs, strategy_config=CHAMPION_CONFIG)


# --- classify_entry_action ---------------------------------------------------------


def entry_action_from_complete_conviction() -> object:
    """Classify a complete Entry Conviction score (complete action)."""

    conviction = calculate_entry_conviction(
        EntryConvictionInput(
            trend_score=Decimal("92"),
            flow_score=Decimal("86"),
            positioning_score=Decimal("78"),
            volatility_score=Decimal("74"),
            structure_score=Decimal("90"),
        ),
        strategy_config=CHAMPION_CONFIG,
    )
    return classify_entry_action(conviction.score, strategy_config=CHAMPION_CONFIG)


def entry_action_score_missing() -> object:
    """Entry Conviction incomplete: ENTRY_ACTION_SCORE_MISSING, complete False."""

    return classify_entry_action(None, strategy_config=CHAMPION_CONFIG)


def entry_action_exceptional_boundary() -> object:
    """A score exactly at the champion exceptional_min threshold."""

    score = Decimal(str(CHAMPION_CONFIG.entry_thresholds.exceptional_min))
    return classify_entry_action(score, strategy_config=CHAMPION_CONFIG)


# --- calculate_trend_score ---------------------------------------------------------


def trend_score_default_weights() -> object:
    """Complete trend score with the owner's default (champion) component weights."""

    return calculate_trend_score(
        TrendScoreInput(
            z_m4=Decimal("1.25"),
            z_m12=Decimal("0.90"),
            z_20w=Decimal("0.70"),
            structure_score=Decimal("1.0"),
            z_52h=Decimal("-0.15"),
        )
    )


def trend_score_from_upstream_structure() -> object:
    """Structure component from the weekly-structure owner (LH_LL week)."""

    structure = classify_weekly_structure_from_weekly_bars(
        _weekly_bars_from_ranges(ALL_LABEL_WEEKLY_RANGES[:6])
    )[-1]
    assert structure is not None
    return calculate_trend_score(
        TrendScoreInput(
            z_m4=Decimal("-1.40"),
            z_m12=Decimal("-0.95"),
            z_20w=Decimal("-0.80"),
            structure_score=structure.raw_score,
            z_52h=Decimal("-1.10"),
        )
    )


def trend_score_explicit_weights() -> object:
    """Explicit weights mapping (validated branch of the weight contract)."""

    return calculate_trend_score(
        TrendScoreInput(
            z_m4=Decimal("0.10"),
            z_m12=Decimal("-0.05"),
            z_20w=Decimal("0.00"),
            structure_score=Decimal("0.0"),
            z_52h=Decimal("-0.30"),
        ),
        weights=dict(DEFAULT_TREND_SCORE_WEIGHTS),
    )


# --- four_week_momentum_from_daily_bars --------------------------------------------


def four_week_momentum_complete() -> object:
    """More than 28 daily bars: the trailing values are defined."""

    bars = _daily_bars(FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS + 12)
    return four_week_momentum_from_daily_bars(bars)


def four_week_momentum_warmup_incomplete() -> object:
    """Fewer than 28 + 1 daily bars: every value is None (warm-up)."""

    bars = _daily_bars(FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS - 8)
    return four_week_momentum_from_daily_bars(bars)


def four_week_momentum_unordered_input() -> object:
    """Bars supplied newest-first: the owner reorders by timestamp."""

    bars = tuple(reversed(_daily_bars(FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS + 3)))
    return four_week_momentum_from_daily_bars(bars)


# --- twelve_week_momentum_from_daily_bars ------------------------------------------


def twelve_week_momentum_complete() -> object:
    """More than 84 daily bars: the trailing values are defined."""

    bars = _daily_bars(TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS + 16)
    return twelve_week_momentum_from_daily_bars(bars)


def twelve_week_momentum_warmup_incomplete() -> object:
    """Fewer than 84 + 1 daily bars: every value is None (warm-up)."""

    bars = _daily_bars(TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS - 24)
    return twelve_week_momentum_from_daily_bars(bars)


# --- twenty_week_ma_distance_from_weekly_bars --------------------------------------


def twenty_week_ma_distance_complete() -> object:
    """More than 20 weekly bars: the trailing distances are defined."""

    bars = _weekly_bars(TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS + 10)
    return twenty_week_ma_distance_from_weekly_bars(bars)


def twenty_week_ma_distance_warmup_incomplete() -> object:
    """Fewer than 20 weekly bars: every distance is None (warm-up)."""

    bars = _weekly_bars(TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS - 8)
    return twenty_week_ma_distance_from_weekly_bars(bars)


# --- fifty_two_week_high_distance_from_weekly_bars ---------------------------------


def fifty_two_week_high_distance_complete() -> object:
    """More than 52 weekly bars (rise, drawdown, recovery): distances defined."""

    bars = _weekly_bars(FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS + 8)
    return fifty_two_week_high_distance_from_weekly_bars(bars)


def fifty_two_week_high_distance_warmup_incomplete() -> object:
    """Fewer than 52 weekly bars: every distance is None (warm-up)."""

    bars = _weekly_bars(FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS - 22)
    return fifty_two_week_high_distance_from_weekly_bars(bars)


# --- classify_weekly_structure_from_weekly_bars ------------------------------------


def weekly_structure_all_labels() -> object:
    """Seven weeks: one classification per later week, every label reached."""

    bars = _weekly_bars_from_ranges(ALL_LABEL_WEEKLY_RANGES)
    return classify_weekly_structure_from_weekly_bars(bars)


def weekly_structure_single_week_incomplete() -> object:
    """One week has no prior week: the only classification is None."""

    bars = _weekly_bars_from_ranges(ALL_LABEL_WEEKLY_RANGES[:1])
    return classify_weekly_structure_from_weekly_bars(bars)


def weekly_structure_unordered_input() -> object:
    """Weeks supplied newest-first: the owner reorders by timestamp."""

    bars = tuple(reversed(_weekly_bars_from_ranges(ALL_LABEL_WEEKLY_RANGES[:4])))
    return classify_weekly_structure_from_weekly_bars(bars)


# --- registry ------------------------------------------------------------------------

FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    "btc_predictor.features.entry.calculate_entry_conviction": (
        entry_conviction_complete,
        entry_conviction_missing_component,
        entry_conviction_from_upstream_trend_owner,
    ),
    "btc_predictor.features.entry.classify_entry_action": (
        entry_action_from_complete_conviction,
        entry_action_score_missing,
        entry_action_exceptional_boundary,
    ),
    "btc_predictor.features.trend.calculate_trend_score": (
        trend_score_default_weights,
        trend_score_from_upstream_structure,
        trend_score_explicit_weights,
    ),
    "btc_predictor.features.momentum.four_week_momentum_from_daily_bars": (
        four_week_momentum_complete,
        four_week_momentum_warmup_incomplete,
        four_week_momentum_unordered_input,
    ),
    "btc_predictor.features.momentum.twelve_week_momentum_from_daily_bars": (
        twelve_week_momentum_complete,
        twelve_week_momentum_warmup_incomplete,
    ),
    "btc_predictor.features.trend.twenty_week_ma_distance_from_weekly_bars": (
        twenty_week_ma_distance_complete,
        twenty_week_ma_distance_warmup_incomplete,
    ),
    "btc_predictor.features.trend.fifty_two_week_high_distance_from_weekly_bars": (
        fifty_two_week_high_distance_complete,
        fifty_two_week_high_distance_warmup_incomplete,
    ),
    "btc_predictor.features.trend.classify_weekly_structure_from_weekly_bars": (
        weekly_structure_all_labels,
        weekly_structure_single_week_incomplete,
        weekly_structure_unordered_input,
    ),
}


# --- RBT-002 R1 runtime cross-check -------------------------------------------------------

import functools as _functools  # noqa: E402

import pytest as _pytest  # noqa: E402

from btc_predictor.research_backtest import input_census as _input_census  # noqa: E402


@_functools.cache
def _census() -> _input_census.DecisionPathCensus:
    return _input_census.discover_decision_path()


@_pytest.mark.parametrize(
    "root, index",
    [(root, index) for root, thunks in sorted(FIXTURES.items()) for index in range(len(thunks))],
)
def test_the_static_census_contains_everything_this_root_traces(root: str, index: int) -> None:
    """Run the root on its synthetic fixture under sys.setprofile: every
    btc_predictor function entered and dataclass constructed must be in the
    static census, and the root itself must have run."""

    result, traced = _input_census.trace_owner_calls(FIXTURES[root][index])
    assert root in traced.functions
    assert _input_census.uncovered_traced(_census(), traced) == {"functions": [], "dataclasses": []}
    if index == 0 and hasattr(result, "complete"):
        assert result.complete is True
