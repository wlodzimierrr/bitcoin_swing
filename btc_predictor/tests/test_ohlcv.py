from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import (
    OhlcvCollectionRequest,
    OhlcvBar,
    build_btc_ohlcv_insert_ignore,
    build_btc_ohlcv_upsert,
    collect_btc_ohlcv,
    derive_ohlcv_bars,
    expected_bar_timestamps,
    missing_bar_timestamps,
    require_utc_datetime,
)


def btc_bar(timestamp: datetime) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=Decimal("100000"),
        high=Decimal("101000"),
        low=Decimal("99000"),
        close=Decimal("100500"),
        volume=Decimal("123.45"),
        provider="coinbase",
        ingested_at=datetime(2026, 8, 25, 12, tzinfo=UTC),
    )


def btc_hourly_bar(timestamp: datetime, offset: int = 0) -> OhlcvBar:
    price = Decimal("100000") + Decimal(offset)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1h",
        open=price,
        high=price + Decimal("10"),
        low=price - Decimal("10"),
        close=price + Decimal("1"),
        volume=Decimal("2"),
        provider="coinbase",
        ingested_at=datetime(2026, 8, 25, 12, tzinfo=UTC),
    )


def hourly_rows(start: datetime, count: int, *, skip_offsets: set[int] | None = None) -> tuple[dict[str, object], ...]:
    skip_offsets = skip_offsets or set()
    return tuple(
        btc_hourly_bar(start + timedelta(hours=offset), offset).as_record()
        for offset in range(count)
        if offset not in skip_offsets
    )


class RecordingConnection:
    def __init__(self) -> None:
        self.statements = []

    def execute(self, statement):
        self.statements.append(statement)


class FlakyProvider:
    def __init__(self, rows: tuple[dict[str, object], ...]) -> None:
        self.rows = rows
        self.calls = 0

    def fetch_ohlcv(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary provider failure")
        assert kwargs["timeframe"] == "1h"
        return self.rows


class StaticProvider:
    def __init__(self, rows: tuple[dict[str, object], ...]) -> None:
        self.rows = rows

    def fetch_ohlcv(self, **kwargs):
        assert kwargs["timeframe"] == "1h"
        return self.rows


def test_btc_ohlcv_upsert_is_idempotent_on_primary_key() -> None:
    statement = build_btc_ohlcv_upsert([btc_bar(datetime(2026, 8, 25, tzinfo=UTC))])
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (timestamp, exchange, symbol, timeframe, provider)" in compiled
    assert "DO UPDATE SET" in compiled
    assert "close = excluded.close" in compiled


def test_btc_ohlcv_insert_ignore_never_changes_existing_records() -> None:
    statement = build_btc_ohlcv_insert_ignore([btc_bar(datetime(2026, 8, 25, tzinfo=UTC))])
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (timestamp, exchange, symbol, timeframe, provider) DO NOTHING" in compiled
    assert "DO UPDATE SET" not in compiled


def test_missing_bar_timestamps_detects_gap() -> None:
    start = datetime(2026, 8, 23, tzinfo=UTC)
    end = datetime(2026, 8, 25, tzinfo=UTC)

    missing = missing_bar_timestamps(
        [start, end],
        start=start,
        end=end,
        timeframe="1d",
    )

    assert missing == (datetime(2026, 8, 24, tzinfo=UTC),)


def test_expected_bar_timestamps_supports_hourly_frequency() -> None:
    assert expected_bar_timestamps(
        start=datetime(2026, 8, 25, 0, tzinfo=UTC),
        end=datetime(2026, 8, 25, 2, tzinfo=UTC),
        timeframe="1h",
    ) == (
        datetime(2026, 8, 25, 0, tzinfo=UTC),
        datetime(2026, 8, 25, 1, tzinfo=UTC),
        datetime(2026, 8, 25, 2, tzinfo=UTC),
    )


def test_expected_bar_timestamps_supports_weekly_frequency() -> None:
    assert expected_bar_timestamps(
        start=datetime(2026, 8, 3, tzinfo=UTC),
        end=datetime(2026, 8, 17, tzinfo=UTC),
        timeframe="1w",
    ) == (
        datetime(2026, 8, 3, tzinfo=UTC),
        datetime(2026, 8, 10, tzinfo=UTC),
        datetime(2026, 8, 17, tzinfo=UTC),
    )


def test_expected_bar_timestamps_supports_monthly_frequency() -> None:
    assert expected_bar_timestamps(
        start=datetime(2026, 1, 1, tzinfo=UTC),
        end=datetime(2026, 4, 1, tzinfo=UTC),
        timeframe="1mo",
    ) == (
        datetime(2026, 1, 1, tzinfo=UTC),
        datetime(2026, 2, 1, tzinfo=UTC),
        datetime(2026, 3, 1, tzinfo=UTC),
        datetime(2026, 4, 1, tzinfo=UTC),
    )


def test_derive_ohlcv_bars_builds_daily_weekly_and_monthly_from_complete_hours() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    source_bars = tuple(
        btc_hourly_bar(start + timedelta(hours=offset), offset)
        for offset in range(31 * 24)
    )

    derived = derive_ohlcv_bars(
        source_bars,
        ("1d", "1w", "1mo"),
        ingested_at=datetime(2026, 2, 1, tzinfo=UTC),
    )

    daily = [bar for bar in derived if bar.timeframe == "1d"]
    weekly = [bar for bar in derived if bar.timeframe == "1w"]
    monthly = [bar for bar in derived if bar.timeframe == "1mo"]

    assert len(daily) == 31
    assert [bar.timestamp for bar in weekly] == [
        datetime(2026, 1, 5, tzinfo=UTC),
        datetime(2026, 1, 12, tzinfo=UTC),
        datetime(2026, 1, 19, tzinfo=UTC),
    ]
    assert len(monthly) == 1
    assert monthly[0].timestamp == datetime(2026, 1, 1, tzinfo=UTC)
    assert monthly[0].open == Decimal("100000")
    assert monthly[0].high == Decimal("100753")
    assert monthly[0].low == Decimal("99990")
    assert monthly[0].close == Decimal("100744")
    assert monthly[0].volume == Decimal("1488")


def test_collect_btc_ohlcv_retries_and_persists_raw_and_complete_derived_bars() -> None:
    start = datetime(2026, 8, 25, tzinfo=UTC)
    request = OhlcvCollectionRequest(
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        start=start,
        end=start + timedelta(hours=23),
        max_attempts=2,
    )
    provider = FlakyProvider(hourly_rows(start, 24))
    connection = RecordingConnection()

    result = collect_btc_ohlcv(
        provider,
        connection,
        request,
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert provider.calls == 2
    assert result.provider_attempts == 2
    assert result.missing_source_timestamps == ()
    assert len(result.raw_bars) == 24
    assert [(bar.timestamp, bar.timeframe) for bar in result.derived_bars] == [
        (start, "1d"),
    ]
    assert len(connection.statements) == 2
    assert all(
        "ON CONFLICT (timestamp, exchange, symbol, timeframe, provider) DO NOTHING"
        in str(statement.compile(dialect=postgresql.dialect()))
        for statement in connection.statements
    )


def test_collect_btc_ohlcv_reports_missing_source_hours_and_skips_incomplete_derivations() -> None:
    start = datetime(2026, 8, 25, tzinfo=UTC)
    request = OhlcvCollectionRequest(
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        start=start,
        end=start + timedelta(hours=23),
    )
    connection = RecordingConnection()

    result = collect_btc_ohlcv(
        StaticProvider(hourly_rows(start, 24, skip_offsets={5})),
        connection,
        request,
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert result.missing_source_timestamps == (start + timedelta(hours=5),)
    assert result.derived_bars == ()
    assert len(connection.statements) == 1


def test_collect_btc_ohlcv_normalizes_provider_timestamps_to_utc() -> None:
    request = OhlcvCollectionRequest(
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        start=datetime(2026, 8, 25, 0, tzinfo=UTC),
        end=datetime(2026, 8, 25, 0, tzinfo=UTC),
        derived_timeframes=(),
    )
    row = btc_hourly_bar(datetime(2026, 8, 25, 0, tzinfo=UTC)).as_record()
    row["timestamp"] = datetime(2026, 8, 25, 1, tzinfo=timezone(timedelta(hours=1)))

    result = collect_btc_ohlcv(
        StaticProvider((row,)),
        RecordingConnection(),
        request,
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )

    assert result.raw_bars[0].timestamp == datetime(2026, 8, 25, 0, tzinfo=UTC)


def test_ohlcv_datetimes_must_be_utc() -> None:
    with pytest.raises(ValueError, match="UTC"):
        require_utc_datetime(datetime(2026, 8, 25), "timestamp")


def test_unsupported_timeframe_fails_fast() -> None:
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        expected_bar_timestamps(
            start=datetime(2026, 8, 25, tzinfo=UTC),
            end=datetime(2026, 8, 25, tzinfo=UTC),
            timeframe="4h",
        )


def test_empty_upsert_batch_fails_fast() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_btc_ohlcv_upsert([])
