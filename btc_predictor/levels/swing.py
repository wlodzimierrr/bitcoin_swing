"""Swing high/low detection for confirmed price levels."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime


WEEKLY_SWING_LEVEL_FEATURE_ID = "WEEKLY_SWING_LEVEL"
MONTHLY_SWING_LEVEL_FEATURE_ID = "MONTHLY_SWING_LEVEL"
WEEKLY_SWING_HIGH = "swing_high"
WEEKLY_SWING_LOW = "swing_low"
WEEKLY_SWING_LEVEL_TYPES = (WEEKLY_SWING_HIGH, WEEKLY_SWING_LOW)
MONTHLY_SWING_HIGH = "swing_high"
MONTHLY_SWING_LOW = "swing_low"
MONTHLY_SWING_LEVEL_TYPES = (MONTHLY_SWING_HIGH, MONTHLY_SWING_LOW)
DEFAULT_WEEKLY_SWING_LEFT_BARS = 3
DEFAULT_WEEKLY_SWING_RIGHT_BARS = 3
DEFAULT_MONTHLY_SWING_LEFT_BARS = 2
DEFAULT_MONTHLY_SWING_RIGHT_BARS = 2


@dataclass(frozen=True)
class WeeklySwingLevel:
    feature_id: str
    level_type: str
    level_timestamp: datetime
    detected_at: datetime
    price: Decimal
    exchange: str
    symbol: str
    timeframe: str
    provider: str
    left_bars: int
    right_bars: int
    source_bar_count: int

    def as_record(self) -> dict[str, Any]:
        level_timestamp = require_utc_datetime(
            self.level_timestamp,
            "level_timestamp",
        )
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        if self.feature_id != WEEKLY_SWING_LEVEL_FEATURE_ID:
            raise ValueError("feature_id must be WEEKLY_SWING_LEVEL")
        if self.level_type not in WEEKLY_SWING_LEVEL_TYPES:
            raise ValueError(f"level_type must be one of {WEEKLY_SWING_LEVEL_TYPES}")
        if detected_at <= level_timestamp:
            raise ValueError("detected_at must be after level_timestamp")
        if self.timeframe != "1w":
            raise ValueError("weekly swing levels require timeframe='1w'")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        if self.left_bars < 1:
            raise ValueError("left_bars must be >= 1")
        if self.right_bars < 1:
            raise ValueError("right_bars must be >= 1")
        if self.source_bar_count < self.left_bars + self.right_bars + 1:
            raise ValueError("source_bar_count must include the full swing window")
        return {
            "feature_id": self.feature_id,
            "level_type": self.level_type,
            "level_timestamp": level_timestamp.isoformat(),
            "detected_at": detected_at.isoformat(),
            "price": str(self.price),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "provider": self.provider,
            "left_bars": self.left_bars,
            "right_bars": self.right_bars,
            "source_bar_count": self.source_bar_count,
        }


@dataclass(frozen=True)
class MonthlySwingLevel:
    feature_id: str
    level_type: str
    level_timestamp: datetime
    detected_at: datetime
    price: Decimal
    exchange: str
    symbol: str
    timeframe: str
    provider: str
    left_bars: int
    right_bars: int
    source_bar_count: int

    def as_record(self) -> dict[str, Any]:
        level_timestamp = require_utc_datetime(
            self.level_timestamp,
            "level_timestamp",
        )
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        if self.feature_id != MONTHLY_SWING_LEVEL_FEATURE_ID:
            raise ValueError("feature_id must be MONTHLY_SWING_LEVEL")
        if self.level_type not in MONTHLY_SWING_LEVEL_TYPES:
            raise ValueError(f"level_type must be one of {MONTHLY_SWING_LEVEL_TYPES}")
        if detected_at <= level_timestamp:
            raise ValueError("detected_at must be after level_timestamp")
        if self.timeframe != "1mo":
            raise ValueError("monthly swing levels require timeframe='1mo'")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        if self.left_bars < 1:
            raise ValueError("left_bars must be >= 1")
        if self.right_bars < 1:
            raise ValueError("right_bars must be >= 1")
        if self.source_bar_count < self.left_bars + self.right_bars + 1:
            raise ValueError("source_bar_count must include the full swing window")
        return {
            "feature_id": self.feature_id,
            "level_type": self.level_type,
            "level_timestamp": level_timestamp.isoformat(),
            "detected_at": detected_at.isoformat(),
            "price": str(self.price),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "provider": self.provider,
            "left_bars": self.left_bars,
            "right_bars": self.right_bars,
            "source_bar_count": self.source_bar_count,
        }


def detect_weekly_swing_levels(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    left_bars: int = DEFAULT_WEEKLY_SWING_LEFT_BARS,
    right_bars: int = DEFAULT_WEEKLY_SWING_RIGHT_BARS,
) -> tuple[WeeklySwingLevel, ...]:
    """Detect confirmed weekly swing highs/lows without future leakage."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_swing_parameters(left_bars=left_bars, right_bars=right_bars)
    _validate_timeframe_bars(bars, timeframe="1w", label="weekly")
    available_bars = _available_bars(
        bars,
        signal_time=signal_time,
        timeframe="1w",
    )
    _validate_single_series(available_bars, label="weekly")

    levels = []
    last_candidate_index = len(available_bars) - right_bars
    for index in range(left_bars, last_candidate_index):
        candidate = available_bars[index]
        window = available_bars[index - left_bars : index + right_bars + 1]
        left_window = window[:left_bars]
        right_window = window[left_bars + 1 :]
        detected_at = _swing_detected_at(window, timeframe="1w")
        if detected_at > signal_time:
            continue
        if _is_swing_high(candidate, (*left_window, *right_window)):
            levels.append(
                _weekly_swing_level(
                    candidate,
                    level_type=WEEKLY_SWING_HIGH,
                    price=candidate.high,
                    detected_at=detected_at,
                    left_bars=left_bars,
                    right_bars=right_bars,
                    source_bar_count=len(window),
                )
            )
        if _is_swing_low(candidate, (*left_window, *right_window)):
            levels.append(
                _weekly_swing_level(
                    candidate,
                    level_type=WEEKLY_SWING_LOW,
                    price=candidate.low,
                    detected_at=detected_at,
                    left_bars=left_bars,
                    right_bars=right_bars,
                    source_bar_count=len(window),
                )
            )

    return tuple(sorted(levels, key=lambda level: (level.level_timestamp, level.level_type)))


def detect_monthly_swing_levels(
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    left_bars: int = DEFAULT_MONTHLY_SWING_LEFT_BARS,
    right_bars: int = DEFAULT_MONTHLY_SWING_RIGHT_BARS,
) -> tuple[MonthlySwingLevel, ...]:
    """Detect confirmed monthly swing highs/lows without future leakage."""

    signal_time = require_utc_datetime(as_of, "as_of")
    _validate_swing_parameters(left_bars=left_bars, right_bars=right_bars)
    _validate_timeframe_bars(bars, timeframe="1mo", label="monthly")
    available_bars = _available_bars(
        bars,
        signal_time=signal_time,
        timeframe="1mo",
    )
    _validate_single_series(available_bars, label="monthly")

    levels = []
    last_candidate_index = len(available_bars) - right_bars
    for index in range(left_bars, last_candidate_index):
        candidate = available_bars[index]
        window = available_bars[index - left_bars : index + right_bars + 1]
        left_window = window[:left_bars]
        right_window = window[left_bars + 1 :]
        detected_at = _swing_detected_at(window, timeframe="1mo")
        if detected_at > signal_time:
            continue
        if _is_swing_high(candidate, (*left_window, *right_window)):
            levels.append(
                _monthly_swing_level(
                    candidate,
                    level_type=MONTHLY_SWING_HIGH,
                    price=candidate.high,
                    detected_at=detected_at,
                    left_bars=left_bars,
                    right_bars=right_bars,
                    source_bar_count=len(window),
                )
            )
        if _is_swing_low(candidate, (*left_window, *right_window)):
            levels.append(
                _monthly_swing_level(
                    candidate,
                    level_type=MONTHLY_SWING_LOW,
                    price=candidate.low,
                    detected_at=detected_at,
                    left_bars=left_bars,
                    right_bars=right_bars,
                    source_bar_count=len(window),
                )
            )

    return tuple(sorted(levels, key=lambda level: (level.level_timestamp, level.level_type)))


def _weekly_swing_level(
    candidate: OhlcvBar,
    *,
    level_type: str,
    price: Decimal,
    detected_at: datetime,
    left_bars: int,
    right_bars: int,
    source_bar_count: int,
) -> WeeklySwingLevel:
    return WeeklySwingLevel(
        feature_id=WEEKLY_SWING_LEVEL_FEATURE_ID,
        level_type=level_type,
        level_timestamp=candidate.timestamp,
        detected_at=detected_at,
        price=price,
        exchange=candidate.exchange,
        symbol=candidate.symbol,
        timeframe=candidate.timeframe,
        provider=candidate.provider,
        left_bars=left_bars,
        right_bars=right_bars,
        source_bar_count=source_bar_count,
    )


def _monthly_swing_level(
    candidate: OhlcvBar,
    *,
    level_type: str,
    price: Decimal,
    detected_at: datetime,
    left_bars: int,
    right_bars: int,
    source_bar_count: int,
) -> MonthlySwingLevel:
    return MonthlySwingLevel(
        feature_id=MONTHLY_SWING_LEVEL_FEATURE_ID,
        level_type=level_type,
        level_timestamp=candidate.timestamp,
        detected_at=detected_at,
        price=price,
        exchange=candidate.exchange,
        symbol=candidate.symbol,
        timeframe=candidate.timeframe,
        provider=candidate.provider,
        left_bars=left_bars,
        right_bars=right_bars,
        source_bar_count=source_bar_count,
    )


def _validate_swing_parameters(*, left_bars: int, right_bars: int) -> None:
    if left_bars < 1:
        raise ValueError("left_bars must be >= 1")
    if right_bars < 1:
        raise ValueError("right_bars must be >= 1")


def _validate_timeframe_bars(
    bars: Sequence[OhlcvBar],
    *,
    timeframe: str,
    label: str,
) -> None:
    for bar in bars:
        if bar.timeframe != timeframe:
            raise ValueError(f"{label} swing detection requires canonical {timeframe} bars")


def _available_bars(
    bars: Sequence[OhlcvBar],
    *,
    signal_time: datetime,
    timeframe: str,
) -> tuple[OhlcvBar, ...]:
    available = []
    for bar in bars:
        timestamp = require_utc_datetime(bar.timestamp, "timestamp")
        ingested_at = require_utc_datetime(bar.ingested_at, "ingested_at")
        if (
            next_bar_timestamp(timestamp, timeframe) <= signal_time
            and ingested_at <= signal_time
        ):
            available.append(bar)
    return tuple(sorted(available, key=lambda bar: bar.timestamp))


def _validate_single_series(bars: Sequence[OhlcvBar], *, label: str) -> None:
    identities = {(bar.exchange, bar.symbol, bar.provider, bar.timeframe) for bar in bars}
    if len(identities) > 1:
        raise ValueError(f"{label} swing detection requires one exchange/symbol/provider/timeframe")


def _swing_detected_at(window_bars: Sequence[OhlcvBar], *, timeframe: str) -> datetime:
    """Return when the whole confirmation window had arrived.

    A swing level is only knowable once every bar that decides it is both closed
    and ingested, so availability is the latest of those times across the window,
    not the confirming bar alone. On a contiguous series ingested in order this
    is the confirming bar, so canonical detection times are unchanged.
    """

    return max(
        max(
            next_bar_timestamp(bar.timestamp, timeframe),
            require_utc_datetime(bar.ingested_at, "ingested_at"),
        )
        for bar in window_bars
    )


def _is_swing_high(candidate: OhlcvBar, comparison_bars: Sequence[OhlcvBar]) -> bool:
    return all(candidate.high > bar.high for bar in comparison_bars)


def _is_swing_low(candidate: OhlcvBar, comparison_bars: Sequence[OhlcvBar]) -> bool:
    return all(candidate.low < bar.low for bar in comparison_bars)
