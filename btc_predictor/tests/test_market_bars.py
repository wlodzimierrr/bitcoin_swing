from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import (
    CANONICAL_BTC_MARKET_BAR_SESSION,
    CANONICAL_MARKET_BAR_TIMEFRAMES,
    MarketBarSessionDefinition,
    OhlcvBar,
    build_canonical_market_bars,
)


def hourly_bar(
    timestamp: datetime,
    offset: int = 0,
    *,
    ingested_at: datetime | None = None,
    provider: str = "coinbase",
) -> OhlcvBar:
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
        provider=provider,
        ingested_at=ingested_at or datetime(2026, 2, 1, tzinfo=UTC),
    )


def hourly_bars(
    start: datetime,
    count: int,
    *,
    ingested_at: datetime | None = None,
) -> tuple[OhlcvBar, ...]:
    return tuple(
        hourly_bar(start + timedelta(hours=offset), offset, ingested_at=ingested_at)
        for offset in range(count)
    )


def test_canonical_market_bar_session_documents_utc_boundaries() -> None:
    assert CANONICAL_MARKET_BAR_TIMEFRAMES == ("1d", "1w", "1mo")
    assert CANONICAL_BTC_MARKET_BAR_SESSION.as_record() == {
        "name": "btc_utc",
        "source_timeframe": "1h",
        "daily_session_start_hour_utc": 0,
        "weekly_session_start_weekday_utc": 0,
        "monthly_session_start_day_utc": 1,
        "timezone": "UTC",
    }


def test_canonical_market_bar_session_rejects_non_canonical_boundaries() -> None:
    with pytest.raises(ValueError, match="weekly BTC bars start on Monday"):
        MarketBarSessionDefinition(weekly_session_start_weekday_utc=6)


def test_build_canonical_market_bars_generates_daily_weekly_and_monthly_bars() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)

    derived = build_canonical_market_bars(
        hourly_bars(start, 31 * 24),
        data_available_at=datetime(2026, 2, 1, tzinfo=UTC),
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
    assert all(bar.ingested_at == datetime(2026, 2, 1, tzinfo=UTC) for bar in derived)


def test_build_canonical_market_bars_uses_only_point_in_time_ingested_source_bars() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    bars = list(hourly_bars(start, 24, ingested_at=datetime(2026, 1, 1, 23, tzinfo=UTC)))
    bars[-1] = hourly_bar(
        start + timedelta(hours=23),
        23,
        ingested_at=cutoff + timedelta(minutes=1),
    )

    assert build_canonical_market_bars(bars, data_available_at=cutoff) == ()

    assert build_canonical_market_bars(
        bars,
        data_available_at=cutoff + timedelta(minutes=1),
        timeframes=("1d",),
    )[0].timestamp == start


def test_build_canonical_market_bars_excludes_source_hours_that_have_not_closed() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    cutoff = datetime(2026, 1, 2, 0, 30, tzinfo=UTC)
    bars = (
        *hourly_bars(start, 24, ingested_at=datetime(2026, 1, 2, tzinfo=UTC)),
        hourly_bar(
            datetime(2026, 1, 2, tzinfo=UTC),
            24,
            ingested_at=datetime(2026, 1, 2, 0, 15, tzinfo=UTC),
        ),
    )

    derived = build_canonical_market_bars(
        bars,
        data_available_at=cutoff,
        timeframes=("1d",),
    )

    assert [bar.timestamp for bar in derived] == [start]


def test_build_canonical_market_bars_is_reproducible_for_unsorted_source_bars() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = hourly_bars(start, 24, ingested_at=datetime(2026, 1, 2, tzinfo=UTC))

    first = build_canonical_market_bars(
        bars,
        data_available_at=datetime(2026, 1, 2, tzinfo=UTC),
        timeframes=("1d",),
    )
    second = build_canonical_market_bars(
        tuple(reversed(bars)),
        data_available_at=datetime(2026, 1, 2, tzinfo=UTC),
        timeframes=("1d",),
    )

    assert first == second


def test_build_canonical_market_bars_rejects_mixed_source_series() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    ingested_at = datetime(2026, 1, 1, 3, tzinfo=UTC)
    bars = (
        hourly_bar(start, provider="coinbase", ingested_at=ingested_at),
        hourly_bar(start + timedelta(hours=1), provider="kraken", ingested_at=ingested_at),
    )

    with pytest.raises(ValueError, match="one exchange/symbol/provider/source timeframe"):
        build_canonical_market_bars(
            bars,
            data_available_at=datetime(2026, 1, 2, tzinfo=UTC),
            timeframes=("1d",),
        )


def test_build_canonical_market_bars_requires_utc_cutoff() -> None:
    with pytest.raises(ValueError, match="data_available_at must be timezone-aware UTC"):
        build_canonical_market_bars(
            (),
            data_available_at=datetime(2026, 1, 2),
        )


def test_build_canonical_market_bars_rejects_unsupported_timeframes() -> None:
    with pytest.raises(ValueError, match="Unsupported canonical market-bar timeframe"):
        build_canonical_market_bars(
            (),
            data_available_at=datetime(2026, 1, 2, tzinfo=UTC),
            timeframes=("4h",),
        )
