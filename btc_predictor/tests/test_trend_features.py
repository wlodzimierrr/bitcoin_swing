from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.features import (
    TWENTY_WEEK_MA_DISTANCE_FEATURE_ID,
    TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS,
    moving_average_distance,
    twenty_week_ma_distance,
    twenty_week_ma_distance_from_weekly_bars,
)


def weekly_bar(timestamp: datetime, close: str) -> OhlcvBar:
    price = Decimal(close)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1w",
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal("1"),
        provider="coinbase",
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def test_twenty_week_ma_distance_metadata_is_stable() -> None:
    assert TWENTY_WEEK_MA_DISTANCE_FEATURE_ID == "MA_DISTANCE_20W"
    assert TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS == 20


def test_twenty_week_ma_distance_calculates_price_minus_ma_over_ma() -> None:
    prices = [Decimal("100")] * 19 + [Decimal("120")]

    distance = twenty_week_ma_distance(prices)

    assert distance[:19] == (None,) * 19
    assert distance[19] == Decimal("0.1881188118811881188118811881")


def test_moving_average_distance_supports_custom_windows() -> None:
    assert moving_average_distance([10, 20, 30], window=2) == (
        None,
        Decimal("0.3333333333333333333333333333"),
        Decimal("0.2"),
    )


def test_twenty_week_ma_distance_returns_none_when_ma_is_zero() -> None:
    prices = [Decimal("0")] * 20

    assert twenty_week_ma_distance(prices)[19] is None


def test_twenty_week_ma_distance_uses_only_past_and_current_prices() -> None:
    prices = [Decimal("100")] * 19 + [Decimal("120"), Decimal("1000000")]

    assert twenty_week_ma_distance(prices)[:-1] == twenty_week_ma_distance(prices[:-1])


def test_twenty_week_ma_distance_from_weekly_bars_uses_timestamp_order() -> None:
    start = datetime(2026, 1, 5, tzinfo=UTC)
    bars = tuple(
        weekly_bar(start + timedelta(weeks=offset), "100")
        for offset in range(19)
    ) + (weekly_bar(start + timedelta(weeks=19), "120"),)

    assert twenty_week_ma_distance_from_weekly_bars(tuple(reversed(bars)))[19] == Decimal(
        "0.1881188118811881188118811881"
    )


def test_twenty_week_ma_distance_from_weekly_bars_rejects_non_weekly_bars() -> None:
    daily = OhlcvBar(**{**weekly_bar(datetime(2026, 1, 5, tzinfo=UTC), "100").as_record(), "timeframe": "1d"})

    with pytest.raises(ValueError, match="requires 1w bars"):
        twenty_week_ma_distance_from_weekly_bars([daily])


def test_twenty_week_ma_distance_rejects_invalid_windows() -> None:
    with pytest.raises(ValueError, match="window"):
        twenty_week_ma_distance([1, 2, 3], window=0)
