"""Deterministic synthetic fixtures for the RBT-002 runtime census cross-check.

Group 7: entry triggers (Rulebook 12.1-12.3), the no-chase rule (Rulebook 25)
and the risk-geometry roots (Rulebook 15 and 16.1).

Every thunk builds its inputs from ``btc_predictor`` owner types and the stdlib
only (``Decimal``, ``datetime`` in UTC) and calls its root. Upstream owner
results the composer would hand the root (swing levels, breakout/reclaim
levels, level clusters, ATR, the invalidation / buffer / stop chain) are
produced inside the thunk by calling those owners, so the trace covers the
real composer-facing shapes (owner result objects, not hand-written mappings).

Dates are fixed and synthetic, inside 2021-01-01..2024-12-31. Nothing reads
the wall clock, a random source, the network, a database or a data file; the
only file read is the packaged champion strategy config through
``load_strategy_config()`` (called inside each thunk, as the composer would).
All dates are computed with stdlib ``timedelta`` so the fixture itself never
calls a ``btc_predictor`` helper that the owner would not call.

``FIXTURES`` maps each root path to 1-3 zero-argument thunks. The first thunk
of every root reaches the owner's main path (triggered / complete / selected /
passing); the later thunks reach a refusal, pending or missing-input branch.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.levels.breakout import detect_breakout_reclaim_levels
from btc_predictor.levels.clustering import LevelClusterResult, cluster_price_levels
from btc_predictor.levels.swing import (
    MONTHLY_SWING_LEVEL_FEATURE_ID,
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    MonthlySwingLevel,
    WeeklySwingLevel,
    detect_monthly_swing_levels,
    detect_weekly_swing_levels,
)
from btc_predictor.risk.buffer import atr_from_daily_bars, volatility_buffer_for_invalidation
from btc_predictor.risk.invalidation import (
    BULL_TREND_CONTINUATION_SETUP,
    select_structural_invalidation,
)
from btc_predictor.risk.reward import reward_risk_for_stop
from btc_predictor.risk.stop import initial_stop_for_setup
from btc_predictor.signals.breakout_retest import evaluate_breakout_retest_trigger
from btc_predictor.signals.higher_low import evaluate_higher_low_trigger
from btc_predictor.signals.no_chase import apply_no_chase_filter
from btc_predictor.signals.reclaim import evaluate_reclaim_trigger


EXCHANGE = "coinbase"
SYMBOL = "BTC-USD"
PROVIDER = "coinbase"
ONE_DAY = timedelta(days=1)
ONE_WEEK = timedelta(weeks=1)


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def _bar(
    timestamp: datetime,
    timeframe: str,
    *,
    open_: str,
    high: str,
    low: str,
    close: str,
    closes_at: datetime,
    ingested_at: datetime | None = None,
) -> OhlcvBar:
    """A canonical OHLCV bar ingested when it closes (or later, when given)."""

    return OhlcvBar(
        timestamp=timestamp,
        exchange=EXCHANGE,
        symbol=SYMBOL,
        timeframe=timeframe,
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        provider=PROVIDER,
        ingested_at=closes_at if ingested_at is None else ingested_at,
    )


def _daily(
    timestamp: datetime,
    *,
    high: str,
    low: str,
    close: str,
    open_: str | None = None,
    ingested_at: datetime | None = None,
) -> OhlcvBar:
    return _bar(
        timestamp,
        "1d",
        open_=close if open_ is None else open_,
        high=high,
        low=low,
        close=close,
        closes_at=timestamp + ONE_DAY,
        ingested_at=ingested_at,
    )


def _weekly(timestamp: datetime, *, high: str, low: str) -> OhlcvBar:
    return _bar(timestamp, "1w", open_=low, high=high, low=low, close=high, closes_at=timestamp + ONE_WEEK)


def _monthly(timestamp: datetime, closes_at: datetime, *, open_: str, high: str, low: str, close: str) -> OhlcvBar:
    return _bar(timestamp, "1mo", open_=open_, high=high, low=low, close=close, closes_at=closes_at)


def _flat_daily_history(start: datetime, sessions: int, *, skip: int | None = None) -> tuple[OhlcvBar, ...]:
    """Regular daily sessions 95..105 closing at 100: every true range is 10."""

    return tuple(
        _daily(start + index * ONE_DAY, high="105", low="95", close="100")
        for index in range(sessions)
        if index != skip
    )


# --- Rulebook 12.1 reclaim trigger ------------------------------------------------------
#
# Monthly bars Jan..May 2023 confirm a monthly swing low at 100 (March 2023),
# detected when the May bar closes on 2023-06-01 (champion swing_window_months
# = 2). The 2023-06-02 daily bar trades to 99 and closes at 101: BTC-092
# reclaim, detected 2023-06-03. The follow-up 2023-06-03 bar is the trigger's
# confirmation bar.

RECLAIM_BAR_DAY = _utc(2023, 6, 2)
RECLAIM_DETECTED_AT = _utc(2023, 6, 3)


def _monthly_reclaim_source(config: StrategyConfig) -> MonthlySwingLevel:
    months = (
        _utc(2023, 1, 1),
        _utc(2023, 2, 1),
        _utc(2023, 3, 1),
        _utc(2023, 4, 1),
        _utc(2023, 5, 1),
        _utc(2023, 6, 1),
    )
    rows = (
        ("130", "140", "120", "125"),
        ("125", "130", "110", "115"),
        ("115", "120", "100", "110"),  # swing low 100
        ("110", "125", "105", "120"),
        ("120", "130", "112", "125"),
    )
    bars = tuple(
        _monthly(months[index], months[index + 1], open_=o, high=h, low=lo, close=c)
        for index, (o, h, lo, c) in enumerate(rows)
    )
    window = config.price_levels.swing_window_months
    levels = detect_monthly_swing_levels(bars, as_of=_utc(2023, 6, 1), left_bars=window, right_bars=window)
    return next(level for level in levels if level.level_type == "swing_low")


def _reclaim_inputs(config: StrategyConfig, *, follow_up_low: str = "100") -> tuple[object, tuple[OhlcvBar, ...]]:
    source = _monthly_reclaim_source(config)
    reclaim_bar = _daily(RECLAIM_BAR_DAY, open_="99.5", high="101.5", low="99", close="101")
    levels = detect_breakout_reclaim_levels(
        (source,),
        (reclaim_bar,),
        as_of=RECLAIM_DETECTED_AT,
        breakout_close_buffer_fraction=config.price_levels.breakout_close_buffer_fraction,
        reclaim_close_buffer_fraction=config.price_levels.reclaim_close_buffer_fraction,
    )
    reclaim_level = next(level for level in levels if level.level_type == "reclaim")
    follow_up = _daily(RECLAIM_DETECTED_AT, open_="101", high="103", low=follow_up_low, close="102")
    return reclaim_level, (reclaim_bar, follow_up)


def _reclaim_call(config: StrategyConfig, reclaim_level: object, bars, *, as_of: datetime):
    parameters = config.entry_triggers.reclaim
    return evaluate_reclaim_trigger(
        reclaim_level,
        bars,
        as_of=as_of,
        confirmation_bars=parameters.confirmation_bars,
        hold_buffer_fraction=parameters.hold_buffer_fraction,
        close_buffer_fraction=parameters.close_buffer_fraction,
        config_metadata=config.run_metadata(),
    )


def reclaim_confirmed() -> object:
    """The first closed follow-up bar holds 100 and closes above it: RECLAIM_TRIGGER_CONFIRMED."""

    config = load_strategy_config()
    reclaim_level, bars = _reclaim_inputs(config)
    return _reclaim_call(config, reclaim_level, bars, as_of=_utc(2023, 6, 4))


def reclaim_pending_before_close() -> object:
    """The follow-up session has not closed by as_of: RECLAIM_TRIGGER_CONFIRMATION_PENDING (incomplete)."""

    config = load_strategy_config()
    reclaim_level, bars = _reclaim_inputs(config)
    return _reclaim_call(config, reclaim_level, bars, as_of=_utc(2023, 6, 3, 12))


def reclaim_level_not_held() -> object:
    """The follow-up bar trades back to 99: RECLAIM_TRIGGER_LEVEL_NOT_HELD (complete, not triggered)."""

    config = load_strategy_config()
    reclaim_level, bars = _reclaim_inputs(config, follow_up_low="99")
    return _reclaim_call(config, reclaim_level, bars, as_of=_utc(2023, 6, 4))


# --- Rulebook 12.2 breakout-and-retest trigger ------------------------------------------
#
# Seven weekly bars from Monday 2023-07-03 confirm a weekly swing high at 100
# (week of 2023-07-24), detected 2023-08-21 (champion swing_window_weeks = 3).
# Daily history 2023-07-31..2023-08-21 is flat 95..105 (true range 10). The
# 2023-08-22 bar closes at 106: BTC-092 breakout, detected 2023-08-23. ATR20
# over the sessions visible at breakout detection is known at 2023-08-23.

WEEKLY_HIGH_START = _utc(2023, 7, 3)
BREAKOUT_BAR_DAY = _utc(2023, 8, 22)
BREAKOUT_DETECTED_AT = _utc(2023, 8, 23)


def _weekly_breakout_source(config: StrategyConfig) -> WeeklySwingLevel:
    highs = ("90", "92", "95", "100", "96", "94", "93")
    lows = ("80", "82", "85", "88", "86", "84", "83")
    bars = tuple(
        _weekly(WEEKLY_HIGH_START + index * ONE_WEEK, high=high, low=low)
        for index, (high, low) in enumerate(zip(highs, lows))
    )
    window = config.price_levels.swing_window_weeks
    levels = detect_weekly_swing_levels(bars, as_of=_utc(2023, 8, 21), left_bars=window, right_bars=window)
    return next(level for level in levels if level.level_type == "swing_high")


def _breakout_history() -> tuple[OhlcvBar, ...]:
    history = _flat_daily_history(_utc(2023, 7, 31), 22)  # 2023-07-31 .. 2023-08-21
    breakout_bar = _daily(BREAKOUT_BAR_DAY, open_="100", high="108", low="99", close="106")
    return (*history, breakout_bar)


def _breakout_inputs(config: StrategyConfig) -> tuple[object, tuple[OhlcvBar, ...], Decimal | None]:
    source = _weekly_breakout_source(config)
    history = _breakout_history()
    levels = detect_breakout_reclaim_levels(
        (source,),
        history,
        as_of=BREAKOUT_DETECTED_AT,
        breakout_close_buffer_fraction=config.price_levels.breakout_close_buffer_fraction,
        reclaim_close_buffer_fraction=config.price_levels.reclaim_close_buffer_fraction,
    )
    breakout_level = next(level for level in levels if level.level_type == "breakout")
    atr = atr_from_daily_bars(history, window=config.stop_buffers.atr_period)
    return breakout_level, history, atr


def _breakout_retest_call(config: StrategyConfig, breakout_level, bars, *, as_of: datetime, atr, atr_available_at):
    parameters = config.entry_triggers.breakout_retest
    return evaluate_breakout_retest_trigger(
        breakout_level,
        bars,
        as_of=as_of,
        atr=atr,
        atr_available_at=atr_available_at,
        max_retest_bars=parameters.max_retest_bars,
        max_continuation_bars=parameters.max_continuation_bars,
        retest_distance_atr_max=parameters.retest_distance_atr_max,
        support_breach_atr_max=parameters.support_breach_atr_max,
        continuation_buffer_atr=parameters.continuation_buffer_atr,
        config_metadata=config.run_metadata(),
    )


def breakout_retest_confirmed() -> object:
    """Pullback into the 0.5-ATR zone, support holds, next close clears the retest high: CONFIRMED."""

    config = load_strategy_config()
    breakout_level, history, atr = _breakout_inputs(config)
    retest = _daily(BREAKOUT_DETECTED_AT, open_="104", high="104", low="102", close="103")
    continuation = _daily(_utc(2023, 8, 24), open_="103", high="106", low="101", close="105")
    return _breakout_retest_call(
        config,
        breakout_level,
        (*history, continuation, retest),
        as_of=_utc(2023, 8, 25),
        atr=atr,
        atr_available_at=BREAKOUT_DETECTED_AT,
    )


def breakout_retest_atr_missing() -> object:
    """No ATR supplied (the composer had none): BREAKOUT_RETEST_ATR_MISSING (incomplete)."""

    config = load_strategy_config()
    breakout_level, history, _ = _breakout_inputs(config)
    retest = _daily(BREAKOUT_DETECTED_AT, open_="104", high="104", low="102", close="103")
    return _breakout_retest_call(
        config,
        breakout_level,
        (*history, retest),
        as_of=_utc(2023, 8, 25),
        atr=None,
        atr_available_at=None,
    )


def breakout_retest_support_failed() -> object:
    """The retest bar breaches the 0.25-ATR support floor: BREAKOUT_RETEST_SUPPORT_FAILED (complete)."""

    config = load_strategy_config()
    breakout_level, history, atr = _breakout_inputs(config)
    failed_retest = _daily(BREAKOUT_DETECTED_AT, open_="103", high="103", low="96", close="99")
    return _breakout_retest_call(
        config,
        breakout_level,
        (*history, failed_retest),
        as_of=_utc(2023, 8, 24),
        atr=atr,
        atr_available_at=BREAKOUT_DETECTED_AT,
    )


# --- Rulebook 12.3 higher-low trigger ----------------------------------------------------
#
# Seven weekly bars from Monday 2024-01-01 confirm a weekly swing low at 80
# (week of 2024-01-22), detected 2024-02-19. The daily pattern starts on the
# source low day 2024-01-24: bounce pivot high 100, higher low 85, close 101
# through the pivot on 2024-02-01.

HIGHER_LOW_WEEK_START = _utc(2024, 1, 1)
HIGHER_LOW_AS_OF = _utc(2024, 2, 19)


def _weekly_higher_low_source(config: StrategyConfig) -> WeeklySwingLevel:
    highs = ("100", "105", "110", "120", "111", "108", "107")
    lows = ("90", "88", "85", "80", "86", "89", "91")
    bars = tuple(
        _weekly(HIGHER_LOW_WEEK_START + index * ONE_WEEK, high=high, low=low)
        for index, (high, low) in enumerate(zip(highs, lows))
    )
    window = config.price_levels.swing_window_weeks
    levels = detect_weekly_swing_levels(bars, as_of=HIGHER_LOW_AS_OF, left_bars=window, right_bars=window)
    return next(level for level in levels if level.level_type == "swing_low")


def _higher_low_daily(source: WeeklySwingLevel, *, higher_low: str = "85", include_anchor: bool = True) -> tuple[OhlcvBar, ...]:
    day_zero = source.level_timestamp + 2 * ONE_DAY
    rows = (
        ("84", "80", "82"),  # source swing-low day (low == source price)
        ("85", "82", "85"),
        ("90", "84", "90"),
        ("100", "90", "100"),  # bounce pivot high
        ("96", "88", "96"),
        ("94", higher_low, "94"),  # higher low
        ("95", "87", "95"),
        ("97", "89", "97"),
        ("103", "90", "101"),  # closes above the pivot high
    )
    bars = tuple(
        _daily(day_zero + index * ONE_DAY, high=high, low=low, close=close)
        for index, (high, low, close) in enumerate(rows)
    )
    return bars if include_anchor else bars[1:]


def _higher_low_call(config: StrategyConfig, source: WeeklySwingLevel, bars, *, as_of: datetime):
    parameters = config.entry_triggers.higher_low
    return evaluate_higher_low_trigger(
        source,
        bars,
        as_of=as_of,
        pivot_left_bars=parameters.pivot_left_bars,
        pivot_right_bars=parameters.pivot_right_bars,
        higher_low_left_bars=parameters.higher_low_left_bars,
        higher_low_right_bars=parameters.higher_low_right_bars,
        max_pattern_bars=parameters.max_pattern_bars,
        max_breakout_bars=parameters.max_breakout_bars,
        higher_low_buffer_fraction=parameters.higher_low_buffer_fraction,
        pivot_break_buffer_fraction=parameters.pivot_break_buffer_fraction,
        config_metadata=config.run_metadata(),
    )


def higher_low_confirmed() -> object:
    """Selloff low, bounce pivot, higher low above the source, close through the pivot: CONFIRMED."""

    config = load_strategy_config()
    source = _weekly_higher_low_source(config)
    bars = _higher_low_daily(source)
    return _higher_low_call(config, source, tuple(reversed(bars)), as_of=HIGHER_LOW_AS_OF)


def higher_low_source_bar_missing() -> object:
    """No daily bar in the swing week prints the source low: HIGHER_LOW_SOURCE_BAR_MISSING (incomplete)."""

    config = load_strategy_config()
    source = _weekly_higher_low_source(config)
    bars = _higher_low_daily(source, include_anchor=False)
    return _higher_low_call(config, source, bars, as_of=HIGHER_LOW_AS_OF)


def higher_low_not_above_source() -> object:
    """The confirmed pullback low equals the source low: HIGHER_LOW_NOT_ABOVE_SOURCE (complete)."""

    config = load_strategy_config()
    source = _weekly_higher_low_source(config)
    bars = _higher_low_daily(source, higher_low="80")
    return _higher_low_call(config, source, bars, as_of=HIGHER_LOW_AS_OF)


# --- shared risk geometry (Rulebook 15, 16.1, 25) ----------------------------------------
#
# Decision instant 2024-03-04, entry 100. Point-in-time weekly/monthly swing
# levels: supports 95 (weekly) and 97 (monthly), resistances 125 (weekly) and
# 127 (monthly). BTC-097 clustering at the champion distance fraction (0.025)
# and minimum strength (60) gives one support zone 95..97 and one resistance
# zone 125..127, each with two members, two sources and two timeframes
# (confluence 75). Daily history 2024-02-03..2024-03-03 is flat 95..105, so
# ATR20 = 10, known at 2024-03-04.

DECISION_AS_OF = _utc(2024, 3, 4)
ENTRY_PRICE = Decimal("100")


def _weekly_level(level_type: str, price: str, *, level_timestamp: datetime, detected_at: datetime) -> WeeklySwingLevel:
    return WeeklySwingLevel(
        feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        level_type=level_type,
        level_timestamp=level_timestamp,
        detected_at=detected_at,
        price=Decimal(price),
        exchange=EXCHANGE,
        symbol=SYMBOL,
        timeframe="1w",
        provider=PROVIDER,
        left_bars=3,
        right_bars=3,
        source_bar_count=7,
    )


def _monthly_level(level_type: str, price: str, *, level_timestamp: datetime, detected_at: datetime) -> MonthlySwingLevel:
    return MonthlySwingLevel(
        feature_id=MONTHLY_SWING_LEVEL_FEATURE_ID,
        level_type=level_type,
        level_timestamp=level_timestamp,
        detected_at=detected_at,
        price=Decimal(price),
        exchange=EXCHANGE,
        symbol=SYMBOL,
        timeframe="1mo",
        provider=PROVIDER,
        left_bars=2,
        right_bars=2,
        source_bar_count=5,
    )


def _swing_levels() -> tuple[object, ...]:
    return (
        _weekly_level("swing_low", "95", level_timestamp=_utc(2024, 1, 15), detected_at=_utc(2024, 2, 12)),
        _monthly_level("swing_low", "97", level_timestamp=_utc(2023, 12, 1), detected_at=_utc(2024, 3, 1)),
        _weekly_level("swing_high", "125", level_timestamp=_utc(2024, 1, 8), detected_at=_utc(2024, 2, 5)),
        _monthly_level("swing_high", "127", level_timestamp=_utc(2023, 11, 1), detected_at=_utc(2024, 2, 1)),
    )


def _clusters(config: StrategyConfig, levels: tuple[object, ...] | None = None) -> LevelClusterResult:
    return cluster_price_levels(
        _swing_levels() if levels is None else levels,
        as_of=DECISION_AS_OF,
        reference_price=ENTRY_PRICE,
        cluster_distance_fraction=config.price_levels.cluster_distance_fraction,
        minimum_level_strength=config.price_levels.minimum_level_strength,
    )


def _atr_history(sessions: int = 30, *, skip: int | None = None) -> tuple[OhlcvBar, ...]:
    """Flat sessions ending 2024-03-03 (the last one closes at DECISION_AS_OF)."""

    return _flat_daily_history(DECISION_AS_OF - sessions * ONE_DAY, sessions, skip=skip)


def _atr(config: StrategyConfig, history: tuple[OhlcvBar, ...] | None = None):
    return atr_from_daily_bars(_atr_history() if history is None else history, window=config.stop_buffers.atr_period)


def _invalidation(config: StrategyConfig, clusters: object, *, atr, entry_price: Decimal = ENTRY_PRICE):
    return select_structural_invalidation(
        clusters,
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=entry_price,
        as_of=DECISION_AS_OF,
        atr=atr,
        config_metadata=config.run_metadata(),
    )


def _buffer(config: StrategyConfig, invalidation: object, atr):
    return volatility_buffer_for_invalidation(
        invalidation,
        atr=atr,
        atr_multiplier=config.stop_buffers.atr_multiplier,
        atr_window=config.stop_buffers.atr_period,
        config_metadata=config.run_metadata(),
    )


def _stop(config: StrategyConfig, invalidation: object, buffer: object):
    return initial_stop_for_setup(invalidation, buffer, config_metadata=config.run_metadata())


def _complete_stop(config: StrategyConfig) -> tuple[object, LevelClusterResult]:
    atr = _atr(config)
    clusters = _clusters(config)
    invalidation = _invalidation(config, clusters, atr=atr)
    return _stop(config, invalidation, _buffer(config, invalidation, atr)), clusters


# --- Rulebook 25 no-chase ------------------------------------------------------------------


def _support_zone(clusters: LevelClusterResult):
    return next(cluster for cluster in clusters.clusters if cluster.zone_type == "support")


def _no_chase_call(config: StrategyConfig, entry_zone, *, current_price: Decimal, atr, atr_available_at):
    parameters = config.entry_triggers.no_chase
    return apply_no_chase_filter(
        entry_zone,
        current_price=current_price,
        current_price_available_at=DECISION_AS_OF,
        as_of=DECISION_AS_OF,
        direction="long",
        distance_mode=parameters.distance_mode,
        max_distance_atr=parameters.max_distance_atr,
        max_distance_fraction=parameters.max_distance_fraction,
        atr=atr,
        atr_available_at=atr_available_at,
        config_metadata=config.run_metadata(),
    )


def no_chase_distance_acceptable() -> object:
    """Price 100 is 0.3 ATR above the 95..97 support zone: NO_CHASE_DISTANCE_ACCEPTABLE (complete)."""

    config = load_strategy_config()
    zone = _support_zone(_clusters(config))
    return _no_chase_call(config, zone, current_price=ENTRY_PRICE, atr=_atr(config), atr_available_at=DECISION_AS_OF)


def no_chase_atr_missing() -> object:
    """Price above the zone with no ATR: NO_CHASE_ATR_MISSING (incomplete, blocked)."""

    config = load_strategy_config()
    zone = _support_zone(_clusters(config))
    return _no_chase_call(config, zone, current_price=ENTRY_PRICE, atr=None, atr_available_at=None)


def no_chase_violation() -> object:
    """Price 104 is 0.7 ATR above the zone: NO_CHASE_VIOLATION (complete, blocked)."""

    config = load_strategy_config()
    zone = _support_zone(_clusters(config))
    return _no_chase_call(config, zone, current_price=Decimal("104"), atr=_atr(config), atr_available_at=DECISION_AS_OF)


# --- Rulebook 16.1 structural invalidation --------------------------------------------------


def invalidation_selected() -> object:
    """The BTC-097 LevelClusterResult itself: the 95..97 support zone is selected (invalidation 95)."""

    config = load_strategy_config()
    return _invalidation(config, _clusters(config), atr=_atr(config))


def invalidation_input_missing() -> object:
    """Clustering found no levels (incomplete result, no clusters): STRUCTURAL_INVALIDATION_INPUT_MISSING."""

    config = load_strategy_config()
    return _invalidation(config, _clusters(config, levels=()), atr=_atr(config))


def invalidation_no_candidate() -> object:
    """Entry 130 puts the only support zone 27% away: NO_CANDIDATE / BEYOND_MAX_DISTANCE."""

    config = load_strategy_config()
    return _invalidation(config, _clusters(config).clusters, atr=None, entry_price=Decimal("130"))


# --- Rulebook 16.1 ATR ---------------------------------------------------------------------


def atr_defined() -> object:
    """30 regular sessions over the champion 20-session window: ATR = 10."""

    config = load_strategy_config()
    return atr_from_daily_bars(_atr_history(), window=config.stop_buffers.atr_period)


def atr_warm_up() -> object:
    """Five sessions cannot fill a 20-session window: None (no ATR)."""

    config = load_strategy_config()
    return atr_from_daily_bars(_atr_history(5), window=config.stop_buffers.atr_period)


def atr_window_spans_gap() -> object:
    """A provider-outage gap inside the latest window leaves ATR undefined: None."""

    config = load_strategy_config()
    return atr_from_daily_bars(_atr_history(skip=25), window=config.stop_buffers.atr_period)


# --- Rulebook 16.1 volatility buffer ---------------------------------------------------------


def buffer_complete() -> object:
    """Derived level noise 1 against 0.3 * ATR = 3: ATR-bound buffer of 3 (complete)."""

    config = load_strategy_config()
    atr = _atr(config)
    invalidation = _invalidation(config, _clusters(config), atr=atr)
    return _buffer(config, invalidation, atr)


def buffer_invalidation_incomplete() -> object:
    """BTC-140 refused the selection: VOLATILITY_BUFFER_INVALIDATION_INCOMPLETE."""

    config = load_strategy_config()
    atr = _atr(config)
    invalidation = _invalidation(config, _clusters(config, levels=()), atr=atr)
    return _buffer(config, invalidation, atr)


def buffer_atr_missing() -> object:
    """Complete selection but ATR still warming up (None): VOLATILITY_BUFFER_INPUT_MISSING."""

    config = load_strategy_config()
    atr = _atr(config, _atr_history(5))
    invalidation = _invalidation(config, _clusters(config), atr=atr)
    return _buffer(config, invalidation, atr)


# --- Rulebook 16.1 initial stop ---------------------------------------------------------------


def stop_complete() -> object:
    """Invalidation 95 minus buffer 3: stop 92 below entry 100 (complete)."""

    config = load_strategy_config()
    stop, _ = _complete_stop(config)
    return stop


def stop_buffer_incomplete() -> object:
    """A buffer without ATR propagates: INITIAL_STOP_BUFFER_INCOMPLETE."""

    config = load_strategy_config()
    atr = _atr(config, _atr_history(5))
    invalidation = _invalidation(config, _clusters(config), atr=atr)
    return _stop(config, invalidation, _buffer(config, invalidation, atr))


def stop_invalidation_and_buffer_incomplete() -> object:
    """Refused selection and incomplete buffer: both incompleteness reasons, no stop."""

    config = load_strategy_config()
    atr = _atr(config)
    invalidation = _invalidation(config, _clusters(config, levels=()), atr=atr)
    return _stop(config, invalidation, _buffer(config, invalidation, atr))


# --- Rulebook 15 reward/risk ------------------------------------------------------------------


def reward_risk_pass() -> object:
    """Major 1w/1mo resistance zone at 125: reward 25 over risk 8, RR 3.125 >= 2.0 (passes)."""

    config = load_strategy_config()
    stop, clusters = _complete_stop(config)
    swing_high = _weekly_level("swing_high", "125", level_timestamp=_utc(2024, 1, 8), detected_at=_utc(2024, 2, 5))
    return reward_risk_for_stop(
        stop,
        resistance_clusters=clusters.clusters,
        swing_highs=(swing_high,),
        range_highs=(),
        measured_move=None,
        as_of=DECISION_AS_OF,
        setup=BULL_TREND_CONTINUATION_SETUP,
        config=config,
        config_metadata=config.run_metadata(),
    )


def reward_risk_stop_incomplete() -> object:
    """An incomplete BTC-142 stop: REWARD_RISK_INPUT_MISSING (incomplete)."""

    config = load_strategy_config()
    atr = _atr(config, _atr_history(5))
    clusters = _clusters(config)
    invalidation = _invalidation(config, clusters, atr=atr)
    stop = _stop(config, invalidation, _buffer(config, invalidation, atr))
    return reward_risk_for_stop(
        stop,
        resistance_clusters=clusters.clusters,
        as_of=DECISION_AS_OF,
        setup=BULL_TREND_CONTINUATION_SETUP,
        config=config,
        config_metadata=config.run_metadata(),
    )


def reward_risk_reference_not_yet_available() -> object:
    """The only swing high above entry is detected after as_of, and no config object is passed
    (the owner resolves the setup minimum by loading the champion config itself):
    REWARD_RISK_NO_REWARD_REFERENCE + REWARD_RISK_REFERENCE_NOT_YET_AVAILABLE."""

    config = load_strategy_config()
    stop, _ = _complete_stop(config)
    late_high = _weekly_level("swing_high", "130", level_timestamp=_utc(2024, 2, 12), detected_at=_utc(2024, 3, 11))
    return reward_risk_for_stop(
        stop,
        resistance_clusters=(),
        swing_highs=(late_high,),
        range_highs=(),
        measured_move=None,
        as_of=DECISION_AS_OF,
        setup=BULL_TREND_CONTINUATION_SETUP,
        config_metadata=config.run_metadata(),
    )


FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    "btc_predictor.signals.reclaim.evaluate_reclaim_trigger": (
        reclaim_confirmed,
        reclaim_pending_before_close,
        reclaim_level_not_held,
    ),
    "btc_predictor.signals.breakout_retest.evaluate_breakout_retest_trigger": (
        breakout_retest_confirmed,
        breakout_retest_atr_missing,
        breakout_retest_support_failed,
    ),
    "btc_predictor.signals.higher_low.evaluate_higher_low_trigger": (
        higher_low_confirmed,
        higher_low_source_bar_missing,
        higher_low_not_above_source,
    ),
    "btc_predictor.signals.no_chase.apply_no_chase_filter": (
        no_chase_distance_acceptable,
        no_chase_atr_missing,
        no_chase_violation,
    ),
    "btc_predictor.risk.invalidation.select_structural_invalidation": (
        invalidation_selected,
        invalidation_input_missing,
        invalidation_no_candidate,
    ),
    "btc_predictor.risk.buffer.atr_from_daily_bars": (
        atr_defined,
        atr_warm_up,
        atr_window_spans_gap,
    ),
    "btc_predictor.risk.buffer.volatility_buffer_for_invalidation": (
        buffer_complete,
        buffer_invalidation_incomplete,
        buffer_atr_missing,
    ),
    "btc_predictor.risk.stop.initial_stop_for_setup": (
        stop_complete,
        stop_buffer_incomplete,
        stop_invalidation_and_buffer_incomplete,
    ),
    "btc_predictor.risk.reward.reward_risk_for_stop": (
        reward_risk_pass,
        reward_risk_stop_incomplete,
        reward_risk_reference_not_yet_available,
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
