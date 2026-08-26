"""Data quality checks for market data inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.data.ohlcv import OhlcvBar, missing_bar_timestamps, require_utc_datetime


OHLCV_QUALITY_REASON_CODES = (
    "DUPLICATE_BAR",
    "IMPOSSIBLE_OHLC",
    "MISSING_PERIOD",
    "STALE_DATA",
    "EXTREME_MALFORMED_VALUE",
)


@dataclass(frozen=True)
class OhlcvQualityConfig:
    max_staleness: timedelta | None = None
    max_close_change_fraction: Decimal = Decimal("0.50")
    max_bar_range_fraction: Decimal = Decimal("0.50")
    max_volume: Decimal | None = None

    def __post_init__(self) -> None:
        if self.max_staleness is not None and self.max_staleness <= timedelta(0):
            raise ValueError("max_staleness must be positive")
        if self.max_close_change_fraction <= 0:
            raise ValueError("max_close_change_fraction must be positive")
        if self.max_bar_range_fraction <= 0:
            raise ValueError("max_bar_range_fraction must be positive")
        if self.max_volume is not None and self.max_volume <= 0:
            raise ValueError("max_volume must be positive")


@dataclass(frozen=True)
class OhlcvQualityIssue:
    reason_code: str
    severity: str
    message: str
    timestamp: datetime | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OhlcvQualityReport:
    issues: tuple[OhlcvQualityIssue, ...]

    @property
    def is_valid(self) -> bool:
        return not self.issues

    @property
    def reason_codes(self) -> tuple[str, ...]:
        seen = set()
        ordered_codes = []
        for issue in self.issues:
            if issue.reason_code not in seen:
                ordered_codes.append(issue.reason_code)
                seen.add(issue.reason_code)
        return tuple(ordered_codes)


def validate_ohlcv_quality(
    bars: Sequence[OhlcvBar],
    *,
    start: datetime,
    end: datetime,
    timeframe: str,
    as_of: datetime,
    config: OhlcvQualityConfig | None = None,
) -> OhlcvQualityReport:
    """Run deterministic OHLCV quality checks for one expected timeframe."""

    start = require_utc_datetime(start, "start")
    end = require_utc_datetime(end, "end")
    as_of = require_utc_datetime(as_of, "as_of")
    if end < start:
        raise ValueError("end must be >= start")

    selected_config = config or OhlcvQualityConfig()
    selected_bars = tuple(sorted((bar for bar in bars if bar.timeframe == timeframe), key=_bar_sort_key))
    issues: list[OhlcvQualityIssue] = []
    issues.extend(_duplicate_issues(selected_bars))
    issues.extend(_impossible_ohlc_issues(selected_bars))
    issues.extend(_missing_period_issues(selected_bars, start=start, end=end, timeframe=timeframe))
    issues.extend(_stale_data_issues(selected_bars, timeframe=timeframe, as_of=as_of, config=selected_config))
    issues.extend(_extreme_value_issues(selected_bars, selected_config))
    return OhlcvQualityReport(tuple(issues))


def _duplicate_issues(bars: Sequence[OhlcvBar]) -> tuple[OhlcvQualityIssue, ...]:
    seen = set()
    issues = []
    for bar in bars:
        key = _bar_identity(bar)
        if key in seen:
            issues.append(
                OhlcvQualityIssue(
                    reason_code="DUPLICATE_BAR",
                    severity="error",
                    message="Duplicate OHLCV bar for primary-key identity.",
                    timestamp=bar.timestamp,
                    details={"key": key},
                )
            )
        seen.add(key)
    return tuple(issues)


def _impossible_ohlc_issues(bars: Sequence[OhlcvBar]) -> tuple[OhlcvQualityIssue, ...]:
    issues = []
    for bar in bars:
        bad_prices = bar.open <= 0 or bar.high <= 0 or bar.low <= 0 or bar.close <= 0
        bad_ohlc_order = bar.high < bar.low or bar.high < max(bar.open, bar.close) or bar.low > min(bar.open, bar.close)
        bad_volume = bar.volume < 0
        if bad_prices or bad_ohlc_order or bad_volume:
            issues.append(
                OhlcvQualityIssue(
                    reason_code="IMPOSSIBLE_OHLC",
                    severity="error",
                    message="OHLCV bar violates basic price or volume invariants.",
                    timestamp=bar.timestamp,
                    details={
                        "bad_prices": bad_prices,
                        "bad_ohlc_order": bad_ohlc_order,
                        "bad_volume": bad_volume,
                    },
                )
            )
    return tuple(issues)


def _missing_period_issues(
    bars: Sequence[OhlcvBar],
    *,
    start: datetime,
    end: datetime,
    timeframe: str,
) -> tuple[OhlcvQualityIssue, ...]:
    grouped: dict[tuple[str, str, str, str], list[datetime]] = {}
    for bar in bars:
        grouped.setdefault((bar.exchange, bar.symbol, bar.timeframe, bar.provider), []).append(bar.timestamp)

    issues = []
    for exchange, symbol, bar_timeframe, provider in sorted(grouped):
        missing = missing_bar_timestamps(
            grouped[(exchange, symbol, bar_timeframe, provider)],
            start=start,
            end=end,
            timeframe=timeframe,
        )
        for timestamp in missing:
            issues.append(
                OhlcvQualityIssue(
                    reason_code="MISSING_PERIOD",
                    severity="error",
                    message="Expected OHLCV period is missing.",
                    timestamp=timestamp,
                    details={
                        "exchange": exchange,
                        "symbol": symbol,
                        "timeframe": bar_timeframe,
                        "provider": provider,
                    },
                )
            )
    if not grouped:
        issues.append(
            OhlcvQualityIssue(
                reason_code="MISSING_PERIOD",
                severity="error",
                message="No OHLCV bars were provided for the expected period.",
                timestamp=start,
                details={"timeframe": timeframe},
            )
        )
    return tuple(issues)


def _stale_data_issues(
    bars: Sequence[OhlcvBar],
    *,
    timeframe: str,
    as_of: datetime,
    config: OhlcvQualityConfig,
) -> tuple[OhlcvQualityIssue, ...]:
    if not bars:
        return ()

    latest = max(bar.timestamp for bar in bars)
    max_staleness = config.max_staleness or _default_max_staleness(timeframe)
    if latest < as_of - max_staleness:
        return (
            OhlcvQualityIssue(
                reason_code="STALE_DATA",
                severity="error",
                message="Latest OHLCV bar is older than the allowed staleness threshold.",
                timestamp=latest,
                details={
                    "as_of": as_of.isoformat(),
                    "max_staleness_seconds": int(max_staleness.total_seconds()),
                },
            ),
        )
    return ()


def _extreme_value_issues(
    bars: Sequence[OhlcvBar],
    config: OhlcvQualityConfig,
) -> tuple[OhlcvQualityIssue, ...]:
    issues = []
    previous_close_by_series: dict[tuple[str, str, str, str], Decimal] = {}
    for bar in bars:
        series_key = (bar.exchange, bar.symbol, bar.timeframe, bar.provider)
        if _bar_is_impossible(bar):
            continue

        previous_close = previous_close_by_series.get(series_key)
        bar_range_fraction = (bar.high - bar.low) / bar.close
        close_change_fraction = (
            abs(bar.close - previous_close) / previous_close
            if previous_close is not None and previous_close > 0
            else Decimal("0")
        )
        volume_too_large = config.max_volume is not None and bar.volume > config.max_volume
        if (
            bar_range_fraction > config.max_bar_range_fraction
            or close_change_fraction > config.max_close_change_fraction
            or volume_too_large
        ):
            issues.append(
                OhlcvQualityIssue(
                    reason_code="EXTREME_MALFORMED_VALUE",
                    severity="error",
                    message="OHLCV bar contains an extreme value outside configured thresholds.",
                    timestamp=bar.timestamp,
                    details={
                        "bar_range_fraction": str(bar_range_fraction),
                        "close_change_fraction": str(close_change_fraction),
                        "volume_too_large": volume_too_large,
                    },
                )
            )
        previous_close_by_series[series_key] = bar.close
    return tuple(issues)


def _bar_identity(bar: OhlcvBar) -> tuple[datetime, str, str, str, str]:
    return (bar.timestamp, bar.exchange, bar.symbol, bar.timeframe, bar.provider)


def _bar_sort_key(bar: OhlcvBar) -> tuple[str, str, str, str, datetime]:
    return (bar.exchange, bar.symbol, bar.timeframe, bar.provider, bar.timestamp)


def _bar_is_impossible(bar: OhlcvBar) -> bool:
    return (
        bar.open <= 0
        or bar.high <= 0
        or bar.low <= 0
        or bar.close <= 0
        or bar.high < bar.low
        or bar.high < max(bar.open, bar.close)
        or bar.low > min(bar.open, bar.close)
        or bar.volume < 0
    )


def _default_max_staleness(timeframe: str) -> timedelta:
    if timeframe == "1h":
        return timedelta(hours=2)
    if timeframe == "1d":
        return timedelta(days=2)
    if timeframe == "1w":
        return timedelta(days=14)
    if timeframe == "1mo":
        return timedelta(days=62)
    raise ValueError(f"Unsupported timeframe for staleness check: {timeframe}")
