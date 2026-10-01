"""Deterministic synthetic fixtures for the G6 level / structure decision-path roots.

Every thunk builds its own inputs from ``btc_predictor`` owner types and the
standard library, calls one root and returns the root's result. Upstream level
results are produced by calling the upstream owners inside the thunk, exactly as
the composer would. There is no randomness, no wall clock, no network, no
database and no file input other than the champion strategy configuration,
which is loaded once at import time (outside every thunk) through
``load_strategy_config()``.

Synthetic market (one series: coinbase / BTC-USD / coinbase):

- Monthly bars Jan..Dec 2021: swing high Apr (52000), swing low Jul (27000),
  swing high Aug (42000), swing low Oct (30000) at left/right = 2.
- Weekly bars from Monday 2021-09-06 for 17 weeks: swing low week 4 (30000),
  swing high week 9 (46000), swing low week 12 (36500) at left/right = 3.
- Daily bars are a deterministic path inside each weekly bar (weekly OHLC is
  exactly the aggregate of its seven daily bars). On the daily path the
  monthly 42000 high breaks out on 2021-11-04, the weekly 46000 high breaks
  out on 2021-12-16 and the weekly 36500 low is reclaimed on 2022-01-01.
- Hourly bars interpolate each daily bar (2021-09-06 .. 2022-01-02), so every
  anchored-VWAP anchor used below has hourly coverage from its anchor bar.
- Decision instant: 2022-01-03 01:00 UTC. Every bar is ingested one minute
  after it closes.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.config.strategy import STRUCTURE_SCORE_CONTRACT_VERSION, load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.features.structure import calculate_structure_score_from_clusters
from btc_predictor.levels.anchored_vwap import (
    CapitulationEvent,
    anchored_vwap_anchor_from_breakout_level,
    anchored_vwap_anchor_from_capitulation_event,
    anchored_vwap_anchor_from_swing_level,
    calculate_anchored_vwaps,
)
from btc_predictor.levels.breakout import detect_breakout_reclaim_levels
from btc_predictor.levels.clustering import LEVEL_CLUSTER_RESISTANCE, LEVEL_CLUSTER_SUPPORT, cluster_price_levels
from btc_predictor.levels.strength import calculate_level_strength_from_cluster
from btc_predictor.levels.swing import detect_monthly_swing_levels, detect_weekly_swing_levels
from btc_predictor.levels.volume_profile import calculate_volume_profile_levels
from btc_predictor.risk.buffer import atr_from_daily_bars


# --- champion configuration (loaded once, outside every thunk) --------------------

_CONFIG = load_strategy_config()
_LEVELS = _CONFIG.price_levels
_CONFIG_METADATA = dict(_CONFIG.run_metadata())
_STRUCTURE_WEIGHTS = dict(_CONFIG.scoring_weights.structure_score)
_STRUCTURE_VERSION = STRUCTURE_SCORE_CONTRACT_VERSION


# --- fixed synthetic market ---------------------------------------------------------

EXCHANGE = "coinbase"
SYMBOL = "BTC-USD"
PROVIDER = "coinbase"
INGEST_LAG = timedelta(minutes=1)
CENT = Decimal("0.01")

AS_OF = datetime(2022, 1, 3, 1, 0, tzinfo=UTC)
WEEKLY_START = datetime(2021, 9, 6, tzinfo=UTC)  # a Monday
MONTHLY_START_YEAR = 2021
HOURLY_START = WEEKLY_START
VOLUME_PROFILE_START = datetime(2021, 12, 20, tzinfo=UTC)

# (open, high, low, close, volume); open is the previous close.
WEEKLY_PATH: tuple[tuple[str, str, str, str, str], ...] = (
    ("38000", "40000", "36000", "37000", "7000"),  # 0  2021-09-06
    ("37000", "39000", "35000", "35500", "7700"),  # 1
    ("35500", "38000", "34000", "34500", "8400"),  # 2
    ("34500", "37000", "33000", "33500", "9100"),  # 3
    ("33500", "36000", "30000", "35000", "14000"),  # 4  2021-10-04 swing low 30000
    ("35000", "37500", "32000", "37000", "9800"),  # 5
    ("37000", "39000", "34000", "38500", "8400"),  # 6
    ("38500", "41000", "36000", "40500", "8400"),  # 7
    ("40500", "43000", "38000", "42500", "9100"),  # 8  2021-11-01
    ("42500", "46000", "40000", "44000", "11200"),  # 9  2021-11-08 swing high 46000
    ("44000", "44500", "39000", "40000", "9100"),  # 10
    ("40000", "42000", "37000", "38000", "8400"),  # 11
    ("38000", "41000", "36500", "40000", "9800"),  # 12 2021-11-29 swing low 36500
    ("40000", "43000", "38000", "42500", "8400"),  # 13
    ("42500", "47500", "41000", "47000", "12600"),  # 14 2021-12-13 breakout above 46000
    ("47000", "48000", "44000", "45000", "9100"),  # 15
    ("45000", "45500", "36000", "37000", "16800"),  # 16 2021-12-27 flush, reclaim of 36500
)

MONTHLY_PATH: tuple[tuple[str, str, str, str, str], ...] = (
    ("30000", "34000", "28000", "33000", "31000"),  # Jan
    ("33000", "39000", "32000", "38000", "28000"),  # Feb
    ("38000", "43000", "36000", "41000", "31000"),  # Mar
    ("41000", "52000", "40000", "50000", "45000"),  # Apr swing high 52000
    ("50000", "51000", "35000", "37000", "52000"),  # May
    ("37000", "40000", "29000", "33000", "40000"),  # Jun
    ("33000", "38000", "27000", "36000", "36000"),  # Jul swing low 27000
    ("36000", "42000", "34000", "39000", "30000"),  # Aug swing high 42000
    ("39000", "40500", "33000", "34000", "33000"),  # Sep
    ("34000", "41500", "30000", "40500", "41000"),  # Oct swing low 30000
    ("40500", "46000", "37000", "38000", "39000"),  # Nov
    ("38000", "48000", "36000", "45000", "47000"),  # Dec
)


def _d(value: str | int | Decimal) -> Decimal:
    return Decimal(str(value))


def _next_month(timestamp: datetime) -> datetime:
    if timestamp.month == 12:
        return timestamp.replace(year=timestamp.year + 1, month=1)
    return timestamp.replace(month=timestamp.month + 1)


def _bar(
    timestamp: datetime,
    closes_at: datetime,
    timeframe: str,
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
    *,
    provider: str = PROVIDER,
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
        volume=volume,
        provider=provider,
        ingested_at=closes_at + INGEST_LAG,
    )


def weekly_bars() -> tuple[OhlcvBar, ...]:
    bars = []
    for index, (open_, high, low, close, volume) in enumerate(WEEKLY_PATH):
        start = WEEKLY_START + timedelta(weeks=index)
        bars.append(_bar(start, start + timedelta(weeks=1), "1w", _d(open_), _d(high), _d(low), _d(close), _d(volume)))
    return tuple(bars)


def monthly_bars() -> tuple[OhlcvBar, ...]:
    bars = []
    for index, (open_, high, low, close, volume) in enumerate(MONTHLY_PATH):
        start = datetime(MONTHLY_START_YEAR, index + 1, 1, tzinfo=UTC)
        bars.append(_bar(start, _next_month(start), "1mo", _d(open_), _d(high), _d(low), _d(close), _d(volume)))
    return tuple(bars)


def _week_points(open_: Decimal, high: Decimal, low: Decimal, close: Decimal) -> tuple[Decimal, ...]:
    """Eight path points p0..p7 whose seven daily legs aggregate to the weekly bar."""

    first, second = (low, high) if close >= open_ else (high, low)
    points = (
        open_,
        (open_ + first) / 2,
        first,
        (first + second) / 2,
        second,
        second + (close - second) / 3,
        second + (close - second) * 2 / 3,
        close,
    )
    return tuple(point.quantize(CENT) for point in points)


def daily_bars() -> tuple[OhlcvBar, ...]:
    bars = []
    for week_index, (open_, high, low, close, volume) in enumerate(WEEKLY_PATH):
        points = _week_points(_d(open_), _d(high), _d(low), _d(close))
        daily_volume = _d(volume) / 7
        for day in range(7):
            start = WEEKLY_START + timedelta(weeks=week_index, days=day)
            day_open, day_close = points[day], points[day + 1]
            bars.append(
                _bar(
                    start,
                    start + timedelta(days=1),
                    "1d",
                    day_open,
                    max(day_open, day_close),
                    min(day_open, day_close),
                    day_close,
                    daily_volume.quantize(Decimal("0.0001")),
                )
            )
    return tuple(bars)


def hourly_bars(
    *,
    start: datetime = HOURLY_START,
    zero_volume: bool = False,
    limit: int | None = None,
) -> tuple[OhlcvBar, ...]:
    """Each daily bar from ``start`` split into 24 linearly interpolated hours."""

    bars = []
    for day_bar in daily_bars():
        if day_bar.timestamp < start:
            continue
        step = (day_bar.close - day_bar.open) / 24
        for hour in range(24):
            hour_open = (day_bar.open + step * hour).quantize(CENT)
            hour_close = (day_bar.open + step * (hour + 1)).quantize(CENT)
            weight = Decimal(6 + (hour * 7) % 11) / Decimal(10)
            volume = Decimal("0") if zero_volume else (day_bar.volume / 24 * weight).quantize(Decimal("0.0001"))
            timestamp = day_bar.timestamp + timedelta(hours=hour)
            bars.append(
                _bar(
                    timestamp,
                    timestamp + timedelta(hours=1),
                    "1h",
                    hour_open,
                    max(hour_open, hour_close),
                    min(hour_open, hour_close),
                    hour_close,
                    volume,
                )
            )
            if limit is not None and len(bars) >= limit:
                return tuple(bars)
    return tuple(bars)


def _last_close(as_of: datetime = AS_OF) -> Decimal:
    closed = [bar for bar in daily_bars() if bar.timestamp + timedelta(days=1) <= as_of]
    return closed[-1].close


# --- upstream owner calls used inside thunks ---------------------------------------


def _weekly_levels(as_of: datetime = AS_OF):
    return detect_weekly_swing_levels(
        weekly_bars(),
        as_of=as_of,
        left_bars=_LEVELS.swing_window_weeks,
        right_bars=_LEVELS.swing_window_weeks,
    )


def _monthly_levels(as_of: datetime = AS_OF):
    return detect_monthly_swing_levels(
        monthly_bars(),
        as_of=as_of,
        left_bars=_LEVELS.swing_window_months,
        right_bars=_LEVELS.swing_window_months,
    )


def _breakout_levels(as_of: datetime = AS_OF):
    return detect_breakout_reclaim_levels(
        (*_weekly_levels(as_of), *_monthly_levels(as_of)),
        daily_bars(),
        as_of=as_of,
        breakout_close_buffer_fraction=_LEVELS.breakout_close_buffer_fraction,
        reclaim_close_buffer_fraction=_LEVELS.reclaim_close_buffer_fraction,
    )


def _volume_profile(bars, as_of: datetime = AS_OF):
    return calculate_volume_profile_levels(
        bars,
        as_of=as_of,
        price_source=_LEVELS.volume_profile_price_source,
        bin_size_fraction=_LEVELS.volume_profile_bin_size_fraction,
        value_area_fraction=_LEVELS.volume_profile_value_area_fraction,
        hvn_volume_fraction=_LEVELS.volume_profile_hvn_volume_fraction,
        min_bar_count=_LEVELS.volume_profile_min_bars,
    )


def _capitulation_event(
    *,
    event_timestamp: datetime = datetime(2021, 12, 30, tzinfo=UTC),
    detected_at: datetime = datetime(2021, 12, 31, 0, 1, tzinfo=UTC),
    price: str = "36000",
) -> CapitulationEvent:
    return CapitulationEvent(
        event_timestamp=event_timestamp,
        detected_at=detected_at,
        price=_d(price),
        exchange=EXCHANGE,
        symbol=SYMBOL,
        provider=PROVIDER,
        reason_codes=("CAPITULATION_DISORDERLY_DOWNSIDE",),
    )


def _main_anchors():
    weekly = _weekly_levels()
    monthly = _monthly_levels()
    breakouts = _breakout_levels()
    recent_weekly = [level for level in weekly if level.level_timestamp >= HOURLY_START]
    recent_monthly = [level for level in monthly if level.level_timestamp >= HOURLY_START]
    return (
        *(anchored_vwap_anchor_from_swing_level(level) for level in recent_weekly),
        *(anchored_vwap_anchor_from_swing_level(level) for level in recent_monthly),
        *(anchored_vwap_anchor_from_breakout_level(level) for level in breakouts if level.level_type == "breakout"),
        anchored_vwap_anchor_from_capitulation_event(_capitulation_event()),
    )


def _anchored_vwaps(anchors, bars, as_of: datetime = AS_OF):
    return calculate_anchored_vwaps(
        anchors,
        bars,
        as_of=as_of,
        price_source=_LEVELS.anchored_vwap_price_source,
    )


def _all_level_sources(as_of: datetime = AS_OF):
    return (
        *_weekly_levels(as_of),
        *_monthly_levels(as_of),
        *_breakout_levels(as_of),
        _volume_profile(hourly_bars(start=VOLUME_PROFILE_START), as_of),
        *_anchored_vwaps(_main_anchors(), hourly_bars(), as_of),
    )


def _clusters(levels, *, as_of: datetime = AS_OF, cluster_atr=None):
    return cluster_price_levels(
        levels,
        as_of=as_of,
        reference_price=_last_close(as_of),
        cluster_distance_fraction=_LEVELS.cluster_distance_fraction,
        cluster_atr=cluster_atr,
        minimum_level_strength=_LEVELS.minimum_level_strength,
    )


def _nearest_support(cluster_result, entry: Decimal):
    supports = [
        cluster
        for cluster in cluster_result.clusters
        if cluster.zone_type == LEVEL_CLUSTER_SUPPORT and cluster.center_price <= entry
    ]
    return max(supports, key=lambda cluster: cluster.center_price)


def _strength(cluster, *, reaction_magnitude_fraction=None, volume_percentile=None):
    return calculate_level_strength_from_cluster(
        cluster,
        reaction_magnitude_fraction=reaction_magnitude_fraction,
        volume_percentile=volume_percentile,
        weights=_LEVELS.level_strength_weights,
        timeframe_scores=_LEVELS.level_strength_timeframe_scores,
        touch_count_full=_LEVELS.level_strength_touch_count_full,
        reaction_full_fraction=_LEVELS.level_strength_reaction_full_fraction,
        config_metadata=_CONFIG_METADATA,
    )


def _structure(clusters, *, entry: Decimal, stop: Decimal, level_strength_result):
    return calculate_structure_score_from_clusters(
        clusters,
        entry_price=entry,
        stop_price=stop,
        version=_STRUCTURE_VERSION,
        level_strength_result=level_strength_result,
        weights=_STRUCTURE_WEIGHTS,
        entry_location_full_score_distance_fraction=_LEVELS.entry_location_full_score_distance_fraction,
        entry_location_zero_score_distance_fraction=_LEVELS.entry_location_zero_score_distance_fraction,
        rr_minimum=_LEVELS.rr_minimum,
        rr_preferred_min=_LEVELS.rr_preferred_min,
        rr_preferred_max=_LEVELS.rr_preferred_max,
        config_metadata=_CONFIG_METADATA,
    )


# Synthetic stand-ins for the two LevelStrength inputs no owner produces
# (coverage.py BLK-LEVEL-STRENGTH-INPUTS): used only to reach the complete path.
SYNTHETIC_REACTION_MAGNITUDE_FRACTION = Decimal("0.12")
SYNTHETIC_VOLUME_PERCENTILE = Decimal("70")
SYNTHETIC_STOP = Decimal("35500")


# --- thunks ----------------------------------------------------------------------


# detect_weekly_swing_levels
def weekly_swings_detected():
    """Champion window (3/3) over 17 closed weekly bars: low, high, low detected."""

    return _weekly_levels()


def weekly_swings_insufficient_history():
    """Only five weekly bars are closed at the instant: no full window, no level."""

    return _weekly_levels(WEEKLY_START + timedelta(weeks=5, hours=1))


# detect_monthly_swing_levels
def monthly_swings_detected():
    """Champion window (2/2) over Jan..Dec 2021: two highs and two lows detected."""

    return _monthly_levels()


def monthly_swings_insufficient_history():
    """Only three monthly bars are closed at the instant: no level."""

    return _monthly_levels(datetime(2021, 4, 1, 1, 0, tzinfo=UTC))


# detect_breakout_reclaim_levels
def breakout_reclaim_detected():
    """Weekly+monthly swing levels confirmed on daily bars: two breakouts, one reclaim."""

    return _breakout_levels()


def breakout_reclaim_not_yet_confirmed():
    """At 2021-11-03 the detected source levels have no confirming daily close yet."""

    return _breakout_levels(datetime(2021, 11, 3, 1, 0, tzinfo=UTC))


# calculate_volume_profile_levels
def volume_profile_complete():
    """Two weeks of hourly bars: POC, HVN, VAH and VAL (VOLUME_PROFILE_COMPLETE)."""

    return _volume_profile(hourly_bars(start=VOLUME_PROFILE_START))


def volume_profile_insufficient_bars():
    """Ten hourly bars < volume_profile_min_bars (VOLUME_PROFILE_INSUFFICIENT_BARS)."""

    return _volume_profile(hourly_bars(start=VOLUME_PROFILE_START, limit=10))


def volume_profile_zero_volume():
    """Enough hourly bars but all with zero volume (VOLUME_PROFILE_ZERO_VOLUME)."""

    return _volume_profile(hourly_bars(start=VOLUME_PROFILE_START, zero_volume=True))


# anchored_vwap_anchor_from_swing_level
def swing_anchor_from_weekly_low():
    """Weekly swing low (week 12, 36500) -> major_swing_low anchor."""

    level = next(item for item in _weekly_levels() if item.level_type == "swing_low" and item.price == Decimal("36500"))
    return anchored_vwap_anchor_from_swing_level(level)


def swing_anchor_from_monthly_high():
    """Monthly swing high (Aug 2021, 42000) -> major_swing_high anchor."""

    level = next(item for item in _monthly_levels() if item.level_type == "swing_high" and item.price == Decimal("42000"))
    return anchored_vwap_anchor_from_swing_level(level)


# anchored_vwap_anchor_from_breakout_level
def breakout_anchor_from_weekly_breakout():
    """Daily-confirmed breakout of the weekly 46000 high -> breakout anchor."""

    level = next(
        item
        for item in _breakout_levels()
        if item.level_type == "breakout" and item.price == Decimal("46000")
    )
    return anchored_vwap_anchor_from_breakout_level(level)


# anchored_vwap_anchor_from_capitulation_event
def capitulation_anchor_from_event():
    """The 2021-12-30 flush to 36000 -> capitulation_event anchor."""

    return anchored_vwap_anchor_from_capitulation_event(_capitulation_event())


# calculate_anchored_vwaps
def anchored_vwaps_complete():
    """Swing, breakout and capitulation anchors over hourly bars: every result complete."""

    return _anchored_vwaps(_main_anchors(), hourly_bars())


def anchored_vwaps_not_detected_and_insufficient():
    """One anchor detected after the instant, one with no closed bar after it."""

    anchors = (
        anchored_vwap_anchor_from_capitulation_event(
            _capitulation_event(
                event_timestamp=datetime(2022, 1, 2, 12, 0, tzinfo=UTC),
                detected_at=datetime(2022, 1, 3, 2, 0, tzinfo=UTC),
            )
        ),
        anchored_vwap_anchor_from_capitulation_event(
            _capitulation_event(
                event_timestamp=datetime(2022, 1, 3, 0, 30, tzinfo=UTC),
                detected_at=datetime(2022, 1, 3, 0, 45, tzinfo=UTC),
            )
        ),
    )
    return _anchored_vwaps(anchors, hourly_bars())


def anchored_vwaps_zero_volume():
    """Matching hourly bars after the anchor all carry zero volume."""

    anchors = (anchored_vwap_anchor_from_capitulation_event(_capitulation_event()),)
    return _anchored_vwaps(anchors, hourly_bars(start=datetime(2021, 12, 27, tzinfo=UTC), zero_volume=True))


# cluster_price_levels
def clusters_complete_fractional():
    """Every level producer's output clustered at the champion 2.5% distance."""

    return _clusters(_all_level_sources())


def clusters_sources_not_ready_or_incomplete():
    """Only a future-detected level and incomplete AVWAP results: no member, incomplete."""

    as_of = datetime(2021, 12, 31, 1, 0, tzinfo=UTC)
    reclaim = next(level for level in _breakout_levels() if level.level_type == "reclaim")
    pending_vwaps = _anchored_vwaps(
        (
            anchored_vwap_anchor_from_capitulation_event(
                _capitulation_event(
                    event_timestamp=datetime(2021, 12, 31, 0, 0, tzinfo=UTC),
                    detected_at=datetime(2022, 1, 1, 0, 1, tzinfo=UTC),
                )
            ),
        ),
        hourly_bars(start=datetime(2021, 12, 27, tzinfo=UTC)),
        as_of,
    )
    return _clusters((reclaim, *pending_vwaps), as_of=as_of)


def clusters_atr_normalized_with_duplicates():
    """ATR-normalised clustering (cluster_atr from atr_from_daily_bars), duplicate sources skipped."""

    weekly = _weekly_levels()
    sources = (*_all_level_sources(), *weekly)
    return _clusters(sources, cluster_atr=atr_from_daily_bars(daily_bars()))


# calculate_level_strength_from_cluster
def level_strength_complete():
    """Nearest support cluster with synthetic reaction and volume inputs: complete score."""

    entry = _last_close()
    support = _nearest_support(_clusters(_all_level_sources()), entry)
    return _strength(
        support,
        reaction_magnitude_fraction=SYNTHETIC_REACTION_MAGNITUDE_FRACTION,
        volume_percentile=SYNTHETIC_VOLUME_PERCENTILE,
    )


def level_strength_input_missing():
    """Champion state today: no owner supplies reaction or volume -> LEVEL_STRENGTH_INPUT_MISSING."""

    entry = _last_close()
    support = _nearest_support(_clusters(_all_level_sources()), entry)
    return _strength(support)


# calculate_structure_score_from_clusters
def structure_score_complete():
    """Support below, resistance above, valid risk and a complete LevelStrength."""

    entry = _last_close()
    clusters = _clusters(_all_level_sources())
    strength = _strength(
        _nearest_support(clusters, entry),
        reaction_magnitude_fraction=SYNTHETIC_REACTION_MAGNITUDE_FRACTION,
        volume_percentile=SYNTHETIC_VOLUME_PERCENTILE,
    )
    return _structure(clusters, entry=entry, stop=SYNTHETIC_STOP, level_strength_result=strength)


def structure_score_level_strength_missing():
    """Champion state today: incomplete LevelStrength -> STRUCTURE_SCORE_INPUT_MISSING."""

    entry = _last_close()
    clusters = _clusters(_all_level_sources())
    strength = _strength(_nearest_support(clusters, entry))
    return _structure(clusters, entry=entry, stop=SYNTHETIC_STOP, level_strength_result=strength)


def structure_score_support_missing():
    """Only resistance clusters (as a sequence of LevelCluster) -> STRUCTURE_SCORE_SUPPORT_MISSING."""

    entry = _last_close()
    clusters = _clusters(_all_level_sources())
    resistances = tuple(cluster for cluster in clusters.clusters if cluster.zone_type == LEVEL_CLUSTER_RESISTANCE)
    strength = _strength(
        _nearest_support(clusters, entry),
        reaction_magnitude_fraction=SYNTHETIC_REACTION_MAGNITUDE_FRACTION,
        volume_percentile=SYNTHETIC_VOLUME_PERCENTILE,
    )
    return _structure(resistances, entry=entry, stop=SYNTHETIC_STOP, level_strength_result=strength)


FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    "btc_predictor.levels.swing.detect_weekly_swing_levels": (
        weekly_swings_detected,
        weekly_swings_insufficient_history,
    ),
    "btc_predictor.levels.swing.detect_monthly_swing_levels": (
        monthly_swings_detected,
        monthly_swings_insufficient_history,
    ),
    "btc_predictor.levels.breakout.detect_breakout_reclaim_levels": (
        breakout_reclaim_detected,
        breakout_reclaim_not_yet_confirmed,
    ),
    "btc_predictor.levels.volume_profile.calculate_volume_profile_levels": (
        volume_profile_complete,
        volume_profile_insufficient_bars,
        volume_profile_zero_volume,
    ),
    "btc_predictor.levels.anchored_vwap.anchored_vwap_anchor_from_swing_level": (
        swing_anchor_from_weekly_low,
        swing_anchor_from_monthly_high,
    ),
    "btc_predictor.levels.anchored_vwap.anchored_vwap_anchor_from_breakout_level": (
        breakout_anchor_from_weekly_breakout,
    ),
    "btc_predictor.levels.anchored_vwap.anchored_vwap_anchor_from_capitulation_event": (
        capitulation_anchor_from_event,
    ),
    "btc_predictor.levels.anchored_vwap.calculate_anchored_vwaps": (
        anchored_vwaps_complete,
        anchored_vwaps_not_detected_and_insufficient,
        anchored_vwaps_zero_volume,
    ),
    "btc_predictor.levels.clustering.cluster_price_levels": (
        clusters_complete_fractional,
        clusters_sources_not_ready_or_incomplete,
        clusters_atr_normalized_with_duplicates,
    ),
    "btc_predictor.levels.strength.calculate_level_strength_from_cluster": (
        level_strength_complete,
        level_strength_input_missing,
    ),
    "btc_predictor.features.structure.calculate_structure_score_from_clusters": (
        structure_score_complete,
        structure_score_level_strength_missing,
        structure_score_support_missing,
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
