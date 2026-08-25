"""OHLCV data helpers."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from btc_predictor.db.raw import BTC_OHLCV_PRIMARY_KEY, btc_ohlcv


SUPPORTED_TIMEFRAMES = {
    "1d": timedelta(days=1),
    "1w": timedelta(weeks=1),
}


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

    interval = timeframe_interval(timeframe)
    timestamps = []
    current = start
    while current <= end:
        timestamps.append(current)
        current += interval
    return tuple(timestamps)


def timeframe_interval(timeframe: str) -> timedelta:
    try:
        return SUPPORTED_TIMEFRAMES[timeframe]
    except KeyError as exc:
        supported = ", ".join(sorted(SUPPORTED_TIMEFRAMES))
        raise ValueError(f"Unsupported timeframe {timeframe!r}; expected one of: {supported}") from exc


def require_utc_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be UTC")
    return value.astimezone(UTC)


def records_from_mappings(rows: Iterable[Mapping[str, Any]]) -> tuple[OhlcvBar, ...]:
    return tuple(OhlcvBar(**dict(row)) for row in rows)
