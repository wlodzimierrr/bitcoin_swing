"""Breakout and reclaim level detection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime
from btc_predictor.levels.swing import (
    MONTHLY_SWING_HIGH,
    MONTHLY_SWING_LOW,
    WEEKLY_SWING_HIGH,
    WEEKLY_SWING_LOW,
    MonthlySwingLevel,
    WeeklySwingLevel,
)


BREAKOUT_RECLAIM_LEVEL_FEATURE_ID = "BREAKOUT_RECLAIM_LEVEL"
BREAKOUT_LEVEL_TYPE = "breakout"
RECLAIM_LEVEL_TYPE = "reclaim"
BREAKOUT_RECLAIM_LEVEL_TYPES = (BREAKOUT_LEVEL_TYPE, RECLAIM_LEVEL_TYPE)
BREAKOUT_SUPPORT_ROLE = "support_after_breakout"
RECLAIM_SUPPORT_ROLE = "reclaimed_support"
BREAKOUT_RECLAIM_LEVEL_ROLES = (BREAKOUT_SUPPORT_ROLE, RECLAIM_SUPPORT_ROLE)
BREAKOUT_RECLAIM_REASON_CODES = (
    "BREAKOUT_RECLAIM_INPUT_MISSING",
    "BREAKOUT_CONFIRMED",
    "RECLAIM_CONFIRMED",
)
DEFAULT_BREAKOUT_CLOSE_BUFFER_FRACTION = Decimal("0")
DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION = Decimal("0")


class SourceLevel(Protocol):
    feature_id: str
    level_type: str
    level_timestamp: datetime
    detected_at: datetime
    price: Decimal
    exchange: str
    symbol: str
    provider: str


@dataclass(frozen=True)
class BreakoutReclaimLevel:
    feature_id: str
    level_type: str
    level_role: str
    level_timestamp: datetime
    detected_at: datetime
    confirmation_timestamp: datetime
    price: Decimal
    source_level_feature_id: str
    source_level_type: str
    source_level_timestamp: datetime
    source_level_detected_at: datetime
    confirmation_timeframe: str
    exchange: str
    symbol: str
    provider: str
    close_buffer_fraction: Decimal
    confirming_close: Decimal
    confirming_low: Decimal
    source_bar_count: int
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        level_timestamp = require_utc_datetime(
            self.level_timestamp,
            "level_timestamp",
        )
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        confirmation_timestamp = require_utc_datetime(
            self.confirmation_timestamp,
            "confirmation_timestamp",
        )
        source_level_timestamp = require_utc_datetime(
            self.source_level_timestamp,
            "source_level_timestamp",
        )
        source_level_detected_at = require_utc_datetime(
            self.source_level_detected_at,
            "source_level_detected_at",
        )
        if self.feature_id != BREAKOUT_RECLAIM_LEVEL_FEATURE_ID:
            raise ValueError("feature_id must be BREAKOUT_RECLAIM_LEVEL")
        if self.level_type not in BREAKOUT_RECLAIM_LEVEL_TYPES:
            raise ValueError(f"level_type must be one of {BREAKOUT_RECLAIM_LEVEL_TYPES}")
        if self.level_role not in BREAKOUT_RECLAIM_LEVEL_ROLES:
            raise ValueError(f"level_role must be one of {BREAKOUT_RECLAIM_LEVEL_ROLES}")
        if detected_at < confirmation_timestamp:
            raise ValueError("detected_at must be >= confirmation_timestamp")
        if source_level_detected_at > detected_at:
            raise ValueError("source_level_detected_at must be <= detected_at")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        if self.close_buffer_fraction < 0:
            raise ValueError("close_buffer_fraction must be >= 0")
        if self.confirming_close <= 0:
            raise ValueError("confirming_close must be > 0")
        if self.confirming_low <= 0:
            raise ValueError("confirming_low must be > 0")
        if self.source_bar_count < 1:
            raise ValueError("source_bar_count must be >= 1")
        return {
            "feature_id": self.feature_id,
            "level_type": self.level_type,
            "level_role": self.level_role,
            "level_timestamp": level_timestamp.isoformat(),
            "detected_at": detected_at.isoformat(),
            "confirmation_timestamp": confirmation_timestamp.isoformat(),
            "price": str(self.price),
            "source_level_feature_id": self.source_level_feature_id,
            "source_level_type": self.source_level_type,
            "source_level_timestamp": source_level_timestamp.isoformat(),
            "source_level_detected_at": source_level_detected_at.isoformat(),
            "confirmation_timeframe": self.confirmation_timeframe,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "provider": self.provider,
            "close_buffer_fraction": str(self.close_buffer_fraction),
            "confirming_close": str(self.confirming_close),
            "confirming_low": str(self.confirming_low),
            "source_bar_count": self.source_bar_count,
            "reason_codes": list(self.reason_codes),
        }


def detect_breakout_reclaim_levels(
    source_levels: Sequence[WeeklySwingLevel | MonthlySwingLevel],
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    breakout_close_buffer_fraction: Any = DEFAULT_BREAKOUT_CLOSE_BUFFER_FRACTION,
    reclaim_close_buffer_fraction: Any = DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION,
) -> tuple[BreakoutReclaimLevel, ...]:
    """Detect breakout/reclaim levels from confirmed source levels and closed bars."""

    signal_time = require_utc_datetime(as_of, "as_of")
    breakout_buffer = _non_negative_decimal(
        breakout_close_buffer_fraction,
        "breakout_close_buffer_fraction",
    )
    reclaim_buffer = _non_negative_decimal(
        reclaim_close_buffer_fraction,
        "reclaim_close_buffer_fraction",
    )
    _validate_source_levels(source_levels)
    _validate_confirmation_bars(bars)
    available_bars = _available_confirmation_bars(bars, signal_time=signal_time)

    levels = []
    for source_level in _available_source_levels(source_levels, signal_time=signal_time):
        for bar in available_bars:
            bar_detected_at = _bar_detected_at(bar)
            if bar_detected_at > signal_time:
                continue
            if source_level.detected_at > bar_detected_at:
                continue
            if bar.timestamp <= source_level.level_timestamp:
                continue
            if _series_identity(source_level) != _bar_identity(bar):
                continue
            if _is_breakout(source_level, bar, close_buffer_fraction=breakout_buffer):
                levels.append(
                    _breakout_reclaim_level(
                        source_level,
                        bar,
                        level_type=BREAKOUT_LEVEL_TYPE,
                        level_role=BREAKOUT_SUPPORT_ROLE,
                        close_buffer_fraction=breakout_buffer,
                        detected_at=bar_detected_at,
                        reason_codes=("BREAKOUT_CONFIRMED",),
                        source_bar_count=len(available_bars),
                    )
                )
                break
            if _is_reclaim(source_level, bar, close_buffer_fraction=reclaim_buffer):
                levels.append(
                    _breakout_reclaim_level(
                        source_level,
                        bar,
                        level_type=RECLAIM_LEVEL_TYPE,
                        level_role=RECLAIM_SUPPORT_ROLE,
                        close_buffer_fraction=reclaim_buffer,
                        detected_at=bar_detected_at,
                        reason_codes=("RECLAIM_CONFIRMED",),
                        source_bar_count=len(available_bars),
                    )
                )
                break

    return tuple(
        sorted(
            levels,
            key=lambda level: (
                level.detected_at,
                level.level_timestamp,
                level.level_type,
                level.price,
            ),
        )
    )


def _breakout_reclaim_level(
    source_level: SourceLevel,
    bar: OhlcvBar,
    *,
    level_type: str,
    level_role: str,
    close_buffer_fraction: Decimal,
    detected_at: datetime,
    reason_codes: tuple[str, ...],
    source_bar_count: int,
) -> BreakoutReclaimLevel:
    return BreakoutReclaimLevel(
        feature_id=BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
        level_type=level_type,
        level_role=level_role,
        level_timestamp=bar.timestamp,
        detected_at=detected_at,
        confirmation_timestamp=bar.timestamp,
        price=source_level.price,
        source_level_feature_id=source_level.feature_id,
        source_level_type=source_level.level_type,
        source_level_timestamp=source_level.level_timestamp,
        source_level_detected_at=source_level.detected_at,
        confirmation_timeframe=bar.timeframe,
        exchange=bar.exchange,
        symbol=bar.symbol,
        provider=bar.provider,
        close_buffer_fraction=close_buffer_fraction,
        confirming_close=bar.close,
        confirming_low=bar.low,
        source_bar_count=source_bar_count,
        reason_codes=reason_codes,
    )


def _validate_source_levels(
    source_levels: Sequence[WeeklySwingLevel | MonthlySwingLevel],
) -> None:
    for source_level in source_levels:
        source_level.as_record()
        if source_level.level_type not in (
            WEEKLY_SWING_HIGH,
            WEEKLY_SWING_LOW,
            MONTHLY_SWING_HIGH,
            MONTHLY_SWING_LOW,
        ):
            raise ValueError("source level must be a swing high or swing low")


def _validate_confirmation_bars(bars: Sequence[OhlcvBar]) -> None:
    for bar in bars:
        record = bar.as_record()
        if record["timeframe"] not in ("1d", "1w", "1mo"):
            raise ValueError("breakout/reclaim detection requires canonical bars")
        if record["close"] <= 0:
            raise ValueError("confirmation bar close must be > 0")
        if record["low"] <= 0:
            raise ValueError("confirmation bar low must be > 0")


def _available_source_levels(
    source_levels: Sequence[WeeklySwingLevel | MonthlySwingLevel],
    *,
    signal_time: datetime,
) -> tuple[WeeklySwingLevel | MonthlySwingLevel, ...]:
    return tuple(
        sorted(
            (
                source_level
                for source_level in source_levels
                if source_level.detected_at <= signal_time
            ),
            key=lambda source_level: (
                source_level.detected_at,
                source_level.level_timestamp,
                source_level.level_type,
                source_level.price,
            ),
        )
    )


def _available_confirmation_bars(
    bars: Sequence[OhlcvBar],
    *,
    signal_time: datetime,
) -> tuple[OhlcvBar, ...]:
    available = []
    for bar in bars:
        record = bar.as_record()
        timestamp = record["timestamp"]
        ingested_at = record["ingested_at"]
        if next_bar_timestamp(timestamp, bar.timeframe) <= signal_time and ingested_at <= signal_time:
            available.append(bar)
    return tuple(sorted(available, key=lambda bar: bar.timestamp))


def _bar_detected_at(bar: OhlcvBar) -> datetime:
    record = bar.as_record()
    return max(next_bar_timestamp(record["timestamp"], bar.timeframe), record["ingested_at"])


def _is_breakout(
    source_level: SourceLevel,
    bar: OhlcvBar,
    *,
    close_buffer_fraction: Decimal,
) -> bool:
    if source_level.level_type not in (WEEKLY_SWING_HIGH, MONTHLY_SWING_HIGH):
        return False
    return bar.close > source_level.price * (Decimal("1") + close_buffer_fraction)


def _is_reclaim(
    source_level: SourceLevel,
    bar: OhlcvBar,
    *,
    close_buffer_fraction: Decimal,
) -> bool:
    if source_level.level_type not in (WEEKLY_SWING_LOW, MONTHLY_SWING_LOW):
        return False
    close_threshold = source_level.price * (Decimal("1") + close_buffer_fraction)
    return bar.low <= source_level.price and bar.close > close_threshold


def _series_identity(source_level: SourceLevel) -> tuple[str, str, str]:
    return (source_level.exchange, source_level.symbol, source_level.provider)


def _bar_identity(bar: OhlcvBar) -> tuple[str, str, str]:
    return (bar.exchange, bar.symbol, bar.provider)


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < 0:
        raise ValueError(f"{name} must be >= 0")
    return decimal_value
