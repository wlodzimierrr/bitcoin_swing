from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import (
    OhlcvBar,
    build_btc_ohlcv_upsert,
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


def test_btc_ohlcv_upsert_is_idempotent_on_primary_key() -> None:
    statement = build_btc_ohlcv_upsert([btc_bar(datetime(2026, 8, 25, tzinfo=UTC))])
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "ON CONFLICT (timestamp, exchange, symbol, timeframe, provider)" in compiled
    assert "DO UPDATE SET" in compiled
    assert "close = excluded.close" in compiled


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
