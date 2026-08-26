"""Data quality checks for market data inputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.data.derivatives import (
    FundingRate,
    FuturesBasis,
    Liquidation,
    OpenInterest,
    PerpVolume,
)
from btc_predictor.data.ohlcv import OhlcvBar, missing_bar_timestamps, require_utc_datetime


OHLCV_QUALITY_REASON_CODES = (
    "DUPLICATE_BAR",
    "IMPOSSIBLE_OHLC",
    "MISSING_PERIOD",
    "STALE_DATA",
    "EXTREME_MALFORMED_VALUE",
)

DERIVATIVES_QUALITY_REASON_CODES = (
    "STALE_FUNDING",
    "NEGATIVE_OPEN_INTEREST",
    "PROVIDER_DISCONTINUITY",
    "MISSING_EXCHANGE_SNAPSHOT",
    "UNIT_CHANGE",
)

DerivativesQualityRecord = FundingRate | OpenInterest | FuturesBasis | Liquidation | PerpVolume


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


@dataclass(frozen=True)
class DerivativesQualityConfig:
    expected_exchanges: tuple[str, ...] = ()
    required_snapshot_feeds: tuple[str, ...] = ("open_interest", "perp_volume")
    max_funding_staleness: timedelta = timedelta(hours=9)
    max_snapshot_staleness: timedelta = timedelta(hours=2)
    max_provider_gap: timedelta = timedelta(hours=3)
    funding_gap_buffer: timedelta = timedelta(hours=1)

    def __post_init__(self) -> None:
        for field_name in (
            "max_funding_staleness",
            "max_snapshot_staleness",
            "max_provider_gap",
            "funding_gap_buffer",
        ):
            value = getattr(self, field_name)
            if value <= timedelta(0):
                raise ValueError(f"{field_name} must be positive")
        if not all(exchange.strip() for exchange in self.expected_exchanges):
            raise ValueError("expected_exchanges must contain non-empty exchange names")
        valid_snapshot_feeds = {"open_interest", "perp_volume"}
        unsupported = set(self.required_snapshot_feeds) - valid_snapshot_feeds
        if unsupported:
            raise ValueError(f"Unsupported required snapshot feeds: {sorted(unsupported)}")


@dataclass(frozen=True)
class DerivativesQualityIssue:
    reason_code: str
    severity: str
    message: str
    timestamp: datetime | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DerivativesQualityReport:
    issues: tuple[DerivativesQualityIssue, ...]

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


def validate_derivatives_quality(
    rows: Sequence[DerivativesQualityRecord],
    *,
    as_of: datetime,
    config: DerivativesQualityConfig | None = None,
) -> DerivativesQualityReport:
    """Run deterministic quality checks for typed raw derivatives rows."""

    as_of = require_utc_datetime(as_of, "as_of")
    selected_config = config or DerivativesQualityConfig()
    selected_rows = tuple(sorted(rows, key=_derivatives_sort_key))
    for row in selected_rows:
        require_utc_datetime(row.observation_time, "observation_time")
        require_utc_datetime(row.available_at, "available_at")

    issues: list[DerivativesQualityIssue] = []
    issues.extend(_stale_funding_issues(selected_rows, as_of=as_of, config=selected_config))
    issues.extend(_negative_open_interest_issues(selected_rows))
    issues.extend(_provider_discontinuity_issues(selected_rows, config=selected_config))
    issues.extend(_missing_exchange_snapshot_issues(selected_rows, as_of=as_of, config=selected_config))
    issues.extend(_unit_change_issues(selected_rows))
    return DerivativesQualityReport(tuple(issues))


def _stale_funding_issues(
    rows: Sequence[DerivativesQualityRecord],
    *,
    as_of: datetime,
    config: DerivativesQualityConfig,
) -> tuple[DerivativesQualityIssue, ...]:
    funding_rows = tuple(row for row in rows if isinstance(row, FundingRate))
    exchanges = (
        tuple(sorted(config.expected_exchanges))
        if config.expected_exchanges
        else tuple(sorted({row.exchange for row in funding_rows}))
    )
    issues = []
    for exchange in exchanges:
        available = tuple(
            row
            for row in funding_rows
            if row.exchange == exchange
            and row.available_at <= as_of
            and row.observation_time <= as_of
        )
        if not available:
            issues.append(
                DerivativesQualityIssue(
                    reason_code="STALE_FUNDING",
                    severity="error",
                    message="No funding observation is available for the expected exchange.",
                    details={
                        "exchange": exchange,
                        "as_of": as_of.isoformat(),
                        "max_staleness_seconds": int(config.max_funding_staleness.total_seconds()),
                    },
                )
            )
            continue

        latest = max(available, key=lambda row: row.observation_time)
        if latest.observation_time < as_of - config.max_funding_staleness:
            issues.append(
                DerivativesQualityIssue(
                    reason_code="STALE_FUNDING",
                    severity="error",
                    message="Latest funding observation is older than the allowed staleness threshold.",
                    timestamp=latest.observation_time,
                    details={
                        "exchange": exchange,
                        "symbol": latest.symbol,
                        "instrument": latest.instrument,
                        "provider": latest.provider,
                        "as_of": as_of.isoformat(),
                        "max_staleness_seconds": int(config.max_funding_staleness.total_seconds()),
                    },
                )
            )
    return tuple(issues)


def _negative_open_interest_issues(
    rows: Sequence[DerivativesQualityRecord],
) -> tuple[DerivativesQualityIssue, ...]:
    issues = []
    for row in rows:
        if isinstance(row, OpenInterest) and row.open_interest < 0:
            issues.append(
                DerivativesQualityIssue(
                    reason_code="NEGATIVE_OPEN_INTEREST",
                    severity="error",
                    message="Open interest cannot be negative.",
                    timestamp=row.observation_time,
                    details={
                        "exchange": row.exchange,
                        "symbol": row.symbol,
                        "instrument": row.instrument,
                        "provider": row.provider,
                        "open_interest": str(row.open_interest),
                        "open_interest_unit": row.open_interest_unit,
                    },
                )
            )
    return tuple(issues)


def _provider_discontinuity_issues(
    rows: Sequence[DerivativesQualityRecord],
    *,
    config: DerivativesQualityConfig,
) -> tuple[DerivativesQualityIssue, ...]:
    grouped: dict[tuple[Any, ...], list[DerivativesQualityRecord]] = {}
    for row in rows:
        grouped.setdefault(_derivatives_series_key(row), []).append(row)

    issues = []
    for key in sorted(grouped):
        series = sorted(grouped[key], key=lambda row: row.observation_time)
        for previous, current in zip(series, series[1:]):
            max_gap = _max_provider_gap(previous, config)
            gap = current.observation_time - previous.observation_time
            if gap > max_gap:
                issues.append(
                    DerivativesQualityIssue(
                        reason_code="PROVIDER_DISCONTINUITY",
                        severity="error",
                        message="Provider observations contain a gap larger than the configured threshold.",
                        timestamp=current.observation_time,
                        details={
                            "feed": _derivatives_feed_name(current),
                            "exchange": current.exchange,
                            "symbol": current.symbol,
                            "provider": current.provider,
                            "previous_observation_time": previous.observation_time.isoformat(),
                            "gap_seconds": int(gap.total_seconds()),
                            "max_gap_seconds": int(max_gap.total_seconds()),
                        },
                    )
                )
    return tuple(issues)


def _missing_exchange_snapshot_issues(
    rows: Sequence[DerivativesQualityRecord],
    *,
    as_of: datetime,
    config: DerivativesQualityConfig,
) -> tuple[DerivativesQualityIssue, ...]:
    exchanges = _expected_or_observed_exchanges(config.expected_exchanges, rows)
    issues = []
    for exchange in exchanges:
        for feed_name in config.required_snapshot_feeds:
            available = tuple(
                row
                for row in rows
                if _derivatives_feed_name(row) == feed_name
                and row.exchange == exchange
                and row.available_at <= as_of
                and row.observation_time <= as_of
            )
            fresh = tuple(
                row
                for row in available
                if row.observation_time >= as_of - config.max_snapshot_staleness
            )
            if not fresh:
                latest = max(available, key=lambda row: row.observation_time, default=None)
                issues.append(
                    DerivativesQualityIssue(
                        reason_code="MISSING_EXCHANGE_SNAPSHOT",
                        severity="error",
                        message="Required exchange snapshot feed is missing or stale.",
                        timestamp=latest.observation_time if latest is not None else None,
                        details={
                            "exchange": exchange,
                            "feed": feed_name,
                            "as_of": as_of.isoformat(),
                            "latest_observation_time": (
                                latest.observation_time.isoformat() if latest is not None else None
                            ),
                            "max_snapshot_staleness_seconds": int(
                                config.max_snapshot_staleness.total_seconds()
                            ),
                        },
                    )
                )
    return tuple(issues)


def _unit_change_issues(
    rows: Sequence[DerivativesQualityRecord],
) -> tuple[DerivativesQualityIssue, ...]:
    previous_unit_by_series: dict[tuple[Any, ...], str] = {}
    issues = []
    unit_rows = tuple(
        row for row in rows if isinstance(row, OpenInterest | Liquidation | PerpVolume)
    )
    for row in sorted(unit_rows, key=_derivatives_sort_key):
        key = _unit_series_key(row)
        unit = _row_unit(row)
        previous_unit = previous_unit_by_series.get(key)
        if previous_unit is not None and unit != previous_unit:
            issues.append(
                DerivativesQualityIssue(
                    reason_code="UNIT_CHANGE",
                    severity="error",
                    message="Provider-reported unit changed within the same derivatives series.",
                    timestamp=row.observation_time,
                    details={
                        "feed": _derivatives_feed_name(row),
                        "exchange": row.exchange,
                        "symbol": row.symbol,
                        "provider": row.provider,
                        "previous_unit": previous_unit,
                        "unit": unit,
                    },
                )
            )
        previous_unit_by_series[key] = unit
    return tuple(issues)


def _expected_or_observed_exchanges(
    expected_exchanges: Sequence[str],
    rows: Sequence[DerivativesQualityRecord],
) -> tuple[str, ...]:
    if expected_exchanges:
        return tuple(sorted(expected_exchanges))
    return tuple(sorted({row.exchange for row in rows}))


def _max_provider_gap(row: DerivativesQualityRecord, config: DerivativesQualityConfig) -> timedelta:
    if isinstance(row, FundingRate):
        return timedelta(hours=float(row.funding_interval_hours)) + config.funding_gap_buffer
    return config.max_provider_gap


def _derivatives_feed_name(row: DerivativesQualityRecord) -> str:
    if isinstance(row, FundingRate):
        return "funding_rates"
    if isinstance(row, OpenInterest):
        return "open_interest"
    if isinstance(row, FuturesBasis):
        return "futures_basis"
    if isinstance(row, Liquidation):
        return "liquidations"
    if isinstance(row, PerpVolume):
        return "perp_volume"
    raise TypeError(f"Unsupported derivatives row type: {type(row)!r}")


def _derivatives_series_key(row: DerivativesQualityRecord) -> tuple[Any, ...]:
    feed_name = _derivatives_feed_name(row)
    if isinstance(row, FundingRate | OpenInterest):
        return (feed_name, row.exchange, row.symbol, row.instrument, row.provider)
    if isinstance(row, FuturesBasis):
        return (feed_name, row.exchange, row.symbol, row.instrument, row.expiry, row.provider)
    if isinstance(row, Liquidation):
        return (feed_name, row.exchange, row.symbol, row.timeframe, row.side, row.provider)
    return (feed_name, row.exchange, row.symbol, row.timeframe, row.provider)


def _unit_series_key(row: OpenInterest | Liquidation | PerpVolume) -> tuple[Any, ...]:
    if isinstance(row, OpenInterest):
        return ("open_interest", row.exchange, row.symbol, row.instrument, row.provider)
    if isinstance(row, Liquidation):
        return ("liquidations", row.exchange, row.symbol, row.timeframe, row.side, row.provider)
    return ("perp_volume", row.exchange, row.symbol, row.timeframe, row.provider)


def _row_unit(row: OpenInterest | Liquidation | PerpVolume) -> str:
    if isinstance(row, OpenInterest):
        return row.open_interest_unit
    if isinstance(row, Liquidation):
        return row.quantity_unit
    return row.volume_unit


def _derivatives_sort_key(row: DerivativesQualityRecord) -> tuple[Any, ...]:
    return (*_derivatives_series_key(row), row.observation_time)


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
