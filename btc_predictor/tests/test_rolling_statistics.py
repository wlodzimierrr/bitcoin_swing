from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.features import (
    average_true_range,
    historical_normalize,
    rolling_mean,
    rolling_percentile,
    rolling_volatility,
    rolling_zscore,
    true_ranges,
)


def bar(
    timestamp: datetime,
    *,
    high: str,
    low: str,
    close: str,
) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=Decimal(low),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("1"),
        provider="coinbase",
        ingested_at=datetime(2026, 8, 26, tzinfo=UTC),
    )


def test_rolling_mean_uses_trailing_window_through_current_value() -> None:
    assert rolling_mean([1, 2, 3, 4], window=3) == (
        None,
        None,
        Decimal("2"),
        Decimal("3"),
    )


def test_rolling_volatility_uses_trailing_window_through_current_value() -> None:
    assert rolling_volatility([1, 3, 5], window=2) == (
        None,
        Decimal("1"),
        Decimal("1"),
    )


def test_rolling_zscore_scores_against_prior_window_only() -> None:
    assert rolling_zscore([1, 3, 5], window=2) == (
        None,
        None,
        Decimal("3"),
    )


def test_rolling_percentile_scores_against_prior_window_only() -> None:
    assert rolling_percentile([10, 20, 30, 20], window=3) == (
        None,
        None,
        None,
        Decimal("50.0"),
    )


def test_historical_normalize_uses_prior_window_only() -> None:
    assert historical_normalize([10, 20, 30, 25], window=3) == (
        None,
        None,
        None,
        Decimal("75.00"),
    )


def test_historical_normalize_clips_to_configured_range() -> None:
    assert historical_normalize([10, 20, 30, 50], window=3, lower=0, upper=1) == (
        None,
        None,
        None,
        Decimal("1"),
    )


def test_true_ranges_and_average_true_range_use_previous_close_only() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        bar(start, high="12", low="9", close="11"),
        bar(start + timedelta(days=1), high="13", low="10", close="12"),
        bar(start + timedelta(days=2), high="12", low="8", close="10"),
    )

    assert true_ranges(tuple(reversed(bars))) == (
        Decimal("3"),
        Decimal("3"),
        Decimal("4"),
    )
    assert average_true_range(tuple(reversed(bars)), window=2) == (
        None,
        Decimal("3"),
        Decimal("3.5"),
    )


def test_rolling_calculations_do_not_change_when_future_values_are_appended() -> None:
    values = [1, 2, 3, 4]
    with_future = [*values, 1000000]

    assert rolling_mean(with_future, window=3)[: len(values)] == rolling_mean(values, window=3)
    assert rolling_volatility(with_future, window=2)[: len(values)] == rolling_volatility(
        values,
        window=2,
    )
    assert rolling_zscore(with_future, window=2)[: len(values)] == rolling_zscore(
        values,
        window=2,
    )
    assert rolling_percentile(with_future, window=3)[: len(values)] == rolling_percentile(
        values,
        window=3,
    )
    assert historical_normalize(with_future, window=3)[: len(values)] == historical_normalize(
        values,
        window=3,
    )


def test_atr_does_not_change_when_future_bars_are_appended() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = (
        bar(start, high="12", low="9", close="11"),
        bar(start + timedelta(days=1), high="13", low="10", close="12"),
        bar(start + timedelta(days=2), high="12", low="8", close="10"),
    )
    future_bar = bar(start + timedelta(days=3), high="1000", low="1", close="500")

    assert average_true_range((*bars, future_bar), window=2)[: len(bars)] == average_true_range(
        bars,
        window=2,
    )


def test_rolling_statistics_support_min_periods() -> None:
    assert rolling_mean([1, 2, 3], window=3, min_periods=2) == (
        None,
        Decimal("1.5"),
        Decimal("2"),
    )


def test_rolling_statistics_reject_invalid_windows() -> None:
    with pytest.raises(ValueError, match="window"):
        rolling_mean([1, 2], window=0)


def test_historical_normalize_rejects_invalid_output_range() -> None:
    with pytest.raises(ValueError, match="upper"):
        historical_normalize([1, 2, 3], window=2, lower=100, upper=0)
