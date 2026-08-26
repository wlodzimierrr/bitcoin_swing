from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.features import (
    FOUR_WEEK_MOMENTUM_FEATURE_ID,
    FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS,
    TWELVE_WEEK_MOMENTUM_FEATURE_ID,
    TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS,
    four_week_momentum,
    four_week_momentum_from_daily_bars,
    twelve_week_momentum,
    twelve_week_momentum_from_daily_bars,
)


def daily_bar(timestamp: datetime, close: str) -> OhlcvBar:
    price = Decimal(close)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal("1"),
        provider="coinbase",
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def test_four_week_momentum_metadata_is_stable() -> None:
    assert FOUR_WEEK_MOMENTUM_FEATURE_ID == "MOMENTUM_4W"
    assert FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS == 28


def test_twelve_week_momentum_metadata_is_stable() -> None:
    assert TWELVE_WEEK_MOMENTUM_FEATURE_ID == "MOMENTUM_12W"
    assert TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS == 84


def test_four_week_momentum_calculates_pt_over_pt_minus_28_minus_one() -> None:
    prices = [Decimal("100")] * 28 + [Decimal("110")]

    momentum = four_week_momentum(prices)

    assert momentum[:28] == (None,) * 28
    assert momentum[28] == Decimal("0.1")


def test_twelve_week_momentum_calculates_pt_over_pt_minus_84_minus_one() -> None:
    prices = [Decimal("100")] * 84 + [Decimal("130")]

    momentum = twelve_week_momentum(prices)

    assert momentum[:84] == (None,) * 84
    assert momentum[84] == Decimal("0.3")


def test_four_week_momentum_uses_only_past_prices() -> None:
    prices = [Decimal("100")] * 28 + [Decimal("110"), Decimal("1000000")]

    assert four_week_momentum(prices)[:-1] == four_week_momentum(prices[:-1])


def test_twelve_week_momentum_uses_only_past_prices() -> None:
    prices = [Decimal("100")] * 84 + [Decimal("130"), Decimal("1000000")]

    assert twelve_week_momentum(prices)[:-1] == twelve_week_momentum(prices[:-1])


def test_four_week_momentum_returns_none_when_prior_price_is_zero() -> None:
    prices = [Decimal("0")] * 28 + [Decimal("110")]

    assert four_week_momentum(prices)[28] is None


def test_four_week_momentum_from_daily_bars_uses_timestamp_order() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        daily_bar(start + timedelta(days=offset), "100")
        for offset in range(28)
    ) + (daily_bar(start + timedelta(days=28), "125"),)

    assert four_week_momentum_from_daily_bars(tuple(reversed(bars)))[28] == Decimal("0.25")


def test_twelve_week_momentum_from_daily_bars_uses_timestamp_order() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = tuple(
        daily_bar(start + timedelta(days=offset), "100")
        for offset in range(84)
    ) + (daily_bar(start + timedelta(days=84), "150"),)

    assert twelve_week_momentum_from_daily_bars(tuple(reversed(bars)))[84] == Decimal("0.5")


def test_four_week_momentum_from_daily_bars_rejects_non_daily_bars() -> None:
    hourly = daily_bar(datetime(2026, 1, 1, tzinfo=UTC), "100")
    hourly = OhlcvBar(**{**hourly.as_record(), "timeframe": "1h"})

    with pytest.raises(ValueError, match="requires 1d bars"):
        four_week_momentum_from_daily_bars([hourly])


def test_four_week_momentum_rejects_invalid_lookback() -> None:
    with pytest.raises(ValueError, match="lookback_periods"):
        four_week_momentum([1, 2, 3], lookback_periods=0)
