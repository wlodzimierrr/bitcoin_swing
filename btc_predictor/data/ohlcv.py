"""OHLCV data helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import sleep
from typing import Any, Protocol

from sqlalchemy.dialects.postgresql import insert

from btc_predictor.db.raw import BTC_OHLCV_PRIMARY_KEY, btc_ohlcv


FIXED_TIMEFRAME_INTERVALS = {
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
}
CALENDAR_TIMEFRAMES = ("1mo",)
SUPPORTED_TIMEFRAMES = tuple(sorted((*FIXED_TIMEFRAME_INTERVALS, *CALENDAR_TIMEFRAMES)))
DERIVED_TIMEFRAMES = ("1d", "1w", "1mo")


@dataclass(frozen=True)
class OhlcvBar:
    timestamp: datetime
    exchange: str
    symbol: str
    timeframe: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    provider: str
    ingested_at: datetime

    def as_record(self) -> dict[str, Any]:
        return {
            "timestamp": require_utc_datetime(self.timestamp, "timestamp"),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "provider": self.provider,
            "ingested_at": require_utc_datetime(self.ingested_at, "ingested_at"),
        }


OhlcvRow = OhlcvBar | Mapping[str, Any]


class OhlcvProvider(Protocol):
    """Provider boundary for exchange-specific OHLCV clients."""

    def fetch_ohlcv(
        self,
        *,
        exchange: str,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> Iterable[OhlcvRow]:
        ...


@dataclass(frozen=True)
class OhlcvCollectionRequest:
    exchange: str
    symbol: str
    provider: str
    start: datetime
    end: datetime
    source_timeframe: str = "1h"
    derived_timeframes: tuple[str, ...] = DERIVED_TIMEFRAMES
    max_attempts: int = 3
    retry_backoff_seconds: float = 0

    def __post_init__(self) -> None:
        require_utc_datetime(self.start, "start")
        require_utc_datetime(self.end, "end")
        if self.end < self.start:
            raise ValueError("end must be >= start")
        if self.source_timeframe != "1h":
            raise ValueError("BTC-020 collection currently requires source_timeframe='1h'")
        for timeframe in self.derived_timeframes:
            if timeframe not in DERIVED_TIMEFRAMES:
                raise ValueError(
                    f"Unsupported derived timeframe {timeframe!r}; expected one of: {DERIVED_TIMEFRAMES}"
                )
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be >= 0")


@dataclass(frozen=True)
class OhlcvCollectionResult:
    raw_bars: tuple[OhlcvBar, ...]
    derived_bars: tuple[OhlcvBar, ...]
    missing_source_timestamps: tuple[datetime, ...]
    provider_attempts: int

    @property
    def attempted_bar_count(self) -> int:
        return len(self.raw_bars) + len(self.derived_bars)


class OhlcvCollectionError(RuntimeError):
    """Raised when an OHLCV provider cannot satisfy a collection request."""


def build_btc_ohlcv_upsert(bars: Sequence[OhlcvBar]):
    """Build an idempotent PostgreSQL upsert for raw BTC OHLCV bars."""

    if not bars:
        raise ValueError("bars must contain at least one OHLCV record")

    records = [bar.as_record() for bar in bars]
    statement = insert(btc_ohlcv).values(records)
    update_columns = {
        column.name: statement.excluded[column.name]
        for column in btc_ohlcv.columns
        if column.name not in BTC_OHLCV_PRIMARY_KEY
    }
    return statement.on_conflict_do_update(
        index_elements=list(BTC_OHLCV_PRIMARY_KEY),
        set_=update_columns,
    )


def build_btc_ohlcv_insert_ignore(bars: Sequence[OhlcvBar]):
    """Build an idempotent insert that never changes existing OHLCV records."""

    if not bars:
        raise ValueError("bars must contain at least one OHLCV record")

    records = [bar.as_record() for bar in bars]
    statement = insert(btc_ohlcv).values(records)
    return statement.on_conflict_do_nothing(index_elements=list(BTC_OHLCV_PRIMARY_KEY))


def collect_btc_ohlcv(
    provider: OhlcvProvider,
    connection: Any,
    request: OhlcvCollectionRequest,
    *,
    ingested_at: datetime | None = None,
) -> OhlcvCollectionResult:
    """Fetch raw 1h BTC OHLCV and persist raw plus complete derived bars."""

    ingestion_time = require_utc_datetime(ingested_at or datetime.now(UTC), "ingested_at")
    rows, attempts = _fetch_with_retry(provider, request)
    raw_bars = _normalize_provider_rows(rows, request=request, ingested_at=ingestion_time)
    missing_source_timestamps = missing_bar_timestamps(
        (bar.timestamp for bar in raw_bars),
        start=request.start,
        end=request.end,
        timeframe=request.source_timeframe,
    )
    derived_bars = derive_ohlcv_bars(
        raw_bars,
        request.derived_timeframes,
        ingested_at=ingestion_time,
    )

    if raw_bars:
        connection.execute(build_btc_ohlcv_insert_ignore(raw_bars))
    if derived_bars:
        connection.execute(build_btc_ohlcv_insert_ignore(derived_bars))

    return OhlcvCollectionResult(
        raw_bars=raw_bars,
        derived_bars=derived_bars,
        missing_source_timestamps=missing_source_timestamps,
        provider_attempts=attempts,
    )


def derive_ohlcv_bars(
    source_bars: Sequence[OhlcvBar],
    timeframes: Sequence[str] = DERIVED_TIMEFRAMES,
    *,
    ingested_at: datetime | None = None,
) -> tuple[OhlcvBar, ...]:
    """Aggregate complete 1h bars into daily, weekly, and monthly OHLCV bars."""

    if not source_bars:
        return ()

    ingestion_time = require_utc_datetime(
        ingested_at or max(bar.ingested_at for bar in source_bars),
        "ingested_at",
    )
    hourly_bars = sorted(source_bars, key=lambda bar: bar.timestamp)
    _validate_unique_source_hours(hourly_bars)
    for bar in hourly_bars:
        if bar.timeframe != "1h":
            raise ValueError("derived OHLCV bars require 1h source bars")

    derived: list[OhlcvBar] = []
    for timeframe in timeframes:
        if timeframe not in DERIVED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported derived timeframe {timeframe!r}; expected one of: {DERIVED_TIMEFRAMES}"
            )
        grouped = _group_bars_by_timeframe(hourly_bars, timeframe)
        for bucket_start, bucket_bars in sorted(grouped.items()):
            if _is_complete_bucket(bucket_start, timeframe, bucket_bars):
                derived.append(_aggregate_bucket(bucket_start, timeframe, bucket_bars, ingestion_time))
    return tuple(derived)


def missing_bar_timestamps(
    observed_timestamps: Iterable[datetime],
    *,
    start: datetime,
    end: datetime,
    timeframe: str,
) -> tuple[datetime, ...]:
    """Return expected UTC bar timestamps missing from an observed range."""

    expected = expected_bar_timestamps(start=start, end=end, timeframe=timeframe)
    observed = {require_utc_datetime(value, "observed timestamp") for value in observed_timestamps}
    return tuple(timestamp for timestamp in expected if timestamp not in observed)


def expected_bar_timestamps(
    *,
    start: datetime,
    end: datetime,
    timeframe: str,
) -> tuple[datetime, ...]:
    start = require_utc_datetime(start, "start")
    end = require_utc_datetime(end, "end")
    if end < start:
        raise ValueError("end must be >= start")

    timestamps = []
    current = start
    while current <= end:
        timestamps.append(current)
        current = next_bar_timestamp(current, timeframe)
    return tuple(timestamps)


def timeframe_interval(timeframe: str) -> timedelta:
    try:
        return FIXED_TIMEFRAME_INTERVALS[timeframe]
    except KeyError as exc:
        if timeframe in CALENDAR_TIMEFRAMES:
            raise ValueError(f"Calendar timeframe {timeframe!r} does not have a fixed timedelta") from exc
        supported = ", ".join(SUPPORTED_TIMEFRAMES)
        raise ValueError(f"Unsupported timeframe {timeframe!r}; expected one of: {supported}") from exc


def next_bar_timestamp(timestamp: datetime, timeframe: str) -> datetime:
    timestamp = require_utc_datetime(timestamp, "timestamp")
    if timeframe in FIXED_TIMEFRAME_INTERVALS:
        return timestamp + FIXED_TIMEFRAME_INTERVALS[timeframe]
    if timeframe == "1mo":
        return _add_month(timestamp)
    supported = ", ".join(SUPPORTED_TIMEFRAMES)
    raise ValueError(f"Unsupported timeframe {timeframe!r}; expected one of: {supported}")


def require_utc_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be UTC")
    return value.astimezone(UTC)


def normalize_utc_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def records_from_mappings(rows: Iterable[Mapping[str, Any]]) -> tuple[OhlcvBar, ...]:
    return tuple(OhlcvBar(**dict(row)) for row in rows)


def _fetch_with_retry(
    provider: OhlcvProvider,
    request: OhlcvCollectionRequest,
) -> tuple[tuple[OhlcvRow, ...], int]:
    attempts = 0
    while attempts < request.max_attempts:
        attempts += 1
        try:
            return (
                tuple(
                    provider.fetch_ohlcv(
                        exchange=request.exchange,
                        symbol=request.symbol,
                        timeframe=request.source_timeframe,
                        start=request.start,
                        end=request.end,
                    )
                ),
                attempts,
            )
        except Exception as exc:
            if attempts >= request.max_attempts:
                raise OhlcvCollectionError("OHLCV provider failed after retry attempts") from exc
            if request.retry_backoff_seconds:
                sleep(request.retry_backoff_seconds)
    raise OhlcvCollectionError("OHLCV provider failed without returning data")


def _normalize_provider_rows(
    rows: Iterable[OhlcvRow],
    *,
    request: OhlcvCollectionRequest,
    ingested_at: datetime,
) -> tuple[OhlcvBar, ...]:
    bars = []
    seen_timestamps: set[datetime] = set()
    for row in rows:
        bar = _coerce_provider_row(row, request=request, ingested_at=ingested_at)
        if bar.timestamp in seen_timestamps:
            raise ValueError(f"Duplicate OHLCV source timestamp: {bar.timestamp.isoformat()}")
        seen_timestamps.add(bar.timestamp)
        bars.append(bar)
    return tuple(sorted(bars, key=lambda bar: bar.timestamp))


def _coerce_provider_row(
    row: OhlcvRow,
    *,
    request: OhlcvCollectionRequest,
    ingested_at: datetime,
) -> OhlcvBar:
    if isinstance(row, OhlcvBar):
        source = row.as_record()
    else:
        source = dict(row)

    return OhlcvBar(
        timestamp=normalize_utc_datetime(source["timestamp"], "timestamp"),
        exchange=request.exchange,
        symbol=request.symbol,
        timeframe=request.source_timeframe,
        open=_decimal(source["open"]),
        high=_decimal(source["high"]),
        low=_decimal(source["low"]),
        close=_decimal(source["close"]),
        volume=_decimal(source["volume"]),
        provider=request.provider,
        ingested_at=ingested_at,
    )


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _validate_unique_source_hours(source_bars: Sequence[OhlcvBar]) -> None:
    seen: set[datetime] = set()
    for bar in source_bars:
        if bar.timestamp in seen:
            raise ValueError(f"Duplicate OHLCV source timestamp: {bar.timestamp.isoformat()}")
        seen.add(bar.timestamp)


def _group_bars_by_timeframe(
    source_bars: Sequence[OhlcvBar],
    timeframe: str,
) -> dict[datetime, list[OhlcvBar]]:
    grouped: dict[datetime, list[OhlcvBar]] = {}
    for bar in source_bars:
        bucket_start = _bucket_start(bar.timestamp, timeframe)
        grouped.setdefault(bucket_start, []).append(bar)
    return grouped


def _bucket_start(timestamp: datetime, timeframe: str) -> datetime:
    timestamp = require_utc_datetime(timestamp, "timestamp")
    day_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    if timeframe == "1d":
        return day_start
    if timeframe == "1w":
        return day_start - timedelta(days=day_start.weekday())
    if timeframe == "1mo":
        return day_start.replace(day=1)
    supported = ", ".join(SUPPORTED_TIMEFRAMES)
    raise ValueError(f"Unsupported timeframe {timeframe!r}; expected one of: {supported}")


def _is_complete_bucket(
    bucket_start: datetime,
    timeframe: str,
    bucket_bars: Sequence[OhlcvBar],
) -> bool:
    bucket_end = next_bar_timestamp(bucket_start, timeframe)
    expected_hours = int((bucket_end - bucket_start).total_seconds() // 3600)
    expected_timestamps = expected_bar_timestamps(
        start=bucket_start,
        end=bucket_end - timedelta(hours=1),
        timeframe="1h",
    )
    observed_timestamps = {bar.timestamp for bar in bucket_bars}
    return len(bucket_bars) == expected_hours and all(
        timestamp in observed_timestamps for timestamp in expected_timestamps
    )


def _aggregate_bucket(
    bucket_start: datetime,
    timeframe: str,
    bucket_bars: Sequence[OhlcvBar],
    ingested_at: datetime,
) -> OhlcvBar:
    ordered = sorted(bucket_bars, key=lambda bar: bar.timestamp)
    return OhlcvBar(
        timestamp=bucket_start,
        exchange=ordered[0].exchange,
        symbol=ordered[0].symbol,
        timeframe=timeframe,
        open=ordered[0].open,
        high=max(bar.high for bar in ordered),
        low=min(bar.low for bar in ordered),
        close=ordered[-1].close,
        volume=sum((bar.volume for bar in ordered), Decimal("0")),
        provider=ordered[0].provider,
        ingested_at=ingested_at,
    )


def _add_month(timestamp: datetime) -> datetime:
    month = timestamp.month + 1
    year = timestamp.year
    if month == 13:
        month = 1
        year += 1
    return timestamp.replace(year=year, month=month)
