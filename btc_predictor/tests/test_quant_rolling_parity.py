from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.quant import (
    PARITY_ABSOLUTE_TOLERANCE,
    PARITY_RELATIVE_TOLERANCE,
    NumericInputError,
    average_true_range,
    historical_normalize,
    realized_volatility,
    rolling_mean,
    rolling_percentile,
    rolling_volatility,
    rolling_zscore,
    simple_returns,
    true_range,
)


def decimal_values(values):
    return tuple(Decimal(str(value)) for value in values)


def inclusive_windows(values, window):
    return tuple(
        values[max(0, index - window + 1) : index + 1]
        for index in range(len(values))
    )


def prior_windows(values, window):
    return tuple(
        values[max(0, index - window) : index]
        for index in range(len(values))
    )


def mean(values):
    return sum(values, Decimal("0")) / Decimal(len(values))


def deviation(values, sample=False):
    average = mean(values)
    denominator = Decimal(len(values) - int(sample))
    return (
        sum(((value - average) ** 2 for value in values), Decimal("0"))
        / denominator
    ).sqrt()


def reference_rolling_mean(values, window, min_periods=None):
    required = window if min_periods is None else min_periods
    values = decimal_values(values)
    return tuple(
        mean(items) if len(items) >= required else None
        for items in inclusive_windows(values, window)
    )


def reference_rolling_volatility(values, window, min_periods=None, sample=False):
    required = window if min_periods is None else min_periods
    values = decimal_values(values)
    return tuple(
        deviation(items, sample=sample)
        if len(items) >= required and len(items) > int(sample)
        else None
        for items in inclusive_windows(values, window)
    )


def reference_rolling_zscore(values, window, min_periods=None, sample=False):
    required = window if min_periods is None else min_periods
    values = decimal_values(values)
    output = []
    for value, history in zip(values, prior_windows(values, window)):
        if len(history) < required or len(history) <= int(sample):
            output.append(None)
            continue
        volatility = deviation(history, sample=sample)
        output.append(None if volatility == 0 else (value - mean(history)) / volatility)
    return tuple(output)


def reference_rolling_percentile(values, window, min_periods=None):
    required = window if min_periods is None else min_periods
    values = decimal_values(values)
    output = []
    for value, history in zip(values, prior_windows(values, window)):
        if len(history) < required:
            output.append(None)
            continue
        less = sum(item < value for item in history)
        equal = sum(item == value for item in history)
        rank = Decimal(less) + Decimal("0.5") * Decimal(equal)
        output.append(rank / Decimal(len(history)) * Decimal("100"))
    return tuple(output)


def reference_historical_normalize(
    values,
    window,
    min_periods=None,
    lower=Decimal("0"),
    upper=Decimal("100"),
):
    required = window if min_periods is None else min_periods
    values = decimal_values(values)
    lower = Decimal(str(lower))
    upper = Decimal(str(upper))
    output = []
    for value, history in zip(values, prior_windows(values, window)):
        if len(history) < required or max(history) == min(history):
            output.append(None)
            continue
        fraction = (value - min(history)) / (max(history) - min(history))
        clipped = min(max(fraction, Decimal("0")), Decimal("1"))
        output.append(lower + clipped * (upper - lower))
    return tuple(output)


def as_expected(values):
    return np.asarray(
        [np.nan if value is None else float(value) for value in values],
        dtype=np.float64,
    )


def assert_parity(actual, expected):
    np.testing.assert_allclose(
        actual,
        as_expected(expected),
        atol=PARITY_ABSOLUTE_TOLERANCE,
        rtol=PARITY_RELATIVE_TOLERANCE,
        equal_nan=True,
    )


@pytest.mark.parametrize("window,min_periods", [(1, None), (3, None), (4, 2)])
def test_rolling_mean_matches_decimal_reference(window, min_periods) -> None:
    values = [100, 100.125, 99.75, 101.5, 98.25, 102]

    assert_parity(
        rolling_mean(values, window=window, min_periods=min_periods),
        reference_rolling_mean(values, window, min_periods),
    )


@pytest.mark.parametrize("sample", [False, True])
def test_rolling_volatility_matches_decimal_reference(sample) -> None:
    values = [1.25, 3.5, -2, 7.125, 7.125, 9]

    assert_parity(
        rolling_volatility(values, window=3, min_periods=2, sample=sample),
        reference_rolling_volatility(values, 3, 2, sample),
    )


@pytest.mark.parametrize("sample", [False, True])
def test_rolling_zscore_matches_prior_only_decimal_reference(sample) -> None:
    values = [10, 12, 9, 15, 15, 20, 11]

    assert_parity(
        rolling_zscore(values, window=3, min_periods=2, sample=sample),
        reference_rolling_zscore(values, 3, 2, sample),
    )


def test_percentile_and_normalization_match_prior_only_decimal_reference() -> None:
    values = [10, 20, 30, 20, 50, 5, 25]

    assert_parity(
        rolling_percentile(values, window=3, min_periods=2),
        reference_rolling_percentile(values, 3, 2),
    )
    assert_parity(
        historical_normalize(
            values,
            window=3,
            min_periods=2,
            lower=-1,
            upper=1,
        ),
        reference_historical_normalize(values, 3, 2, -1, 1),
    )


def test_large_deterministic_sample_matches_decimal_oracle_within_frozen_tolerance() -> None:
    generator = np.random.Generator(np.random.PCG64(43))
    values = generator.normal(loc=100, scale=12, size=128)
    values[20:24] = values[19]

    assert_parity(
        rolling_mean(values, window=20, min_periods=5),
        reference_rolling_mean(values, 20, 5),
    )
    assert_parity(
        rolling_volatility(values, window=20, min_periods=5, sample=True),
        reference_rolling_volatility(values, 20, 5, True),
    )
    assert_parity(
        rolling_zscore(values, window=20, min_periods=5),
        reference_rolling_zscore(values, 20, 5),
    )
    assert_parity(
        rolling_percentile(values, window=20, min_periods=5),
        reference_rolling_percentile(values, 20, 5),
    )
    assert_parity(
        historical_normalize(values, window=20, min_periods=5),
        reference_historical_normalize(values, 20, 5),
    )


def test_extreme_finite_windows_use_stable_intermediate_arithmetic() -> None:
    np.testing.assert_array_equal(
        rolling_mean([1e308, 1e308], window=2),
        [np.nan, 1e308],
    )
    normalized = historical_normalize(
        [-1e308, 1e308, 0],
        window=2,
        min_periods=2,
    )
    np.testing.assert_array_equal(normalized, [np.nan, np.nan, 50])

    with pytest.raises(NumericInputError, match="finite float64 range"):
        realized_volatility(
            [100, 101],
            window=1,
            annualization_periods=10**1000,
        )


def test_returns_true_range_atr_and_realized_volatility_match_reference_math() -> None:
    closes = [100, 110, 99, 108.9, 104]
    highs = [102, 113, 103, 112, 109]
    lows = [98, 106, 95, 97, 100]
    decimal_closes = decimal_values(closes)
    expected_returns = tuple(
        current / previous - Decimal("1")
        for previous, current in zip(decimal_closes, decimal_closes[1:])
    )
    expected_ranges = []
    for index, (high, low, close) in enumerate(
        zip(decimal_values(highs), decimal_values(lows), decimal_closes)
    ):
        if index == 0:
            expected_ranges.append(high - low)
        else:
            expected_ranges.append(
                max(
                    high - low,
                    abs(high - decimal_closes[index - 1]),
                    abs(low - decimal_closes[index - 1]),
                )
            )
    expected_atr = reference_rolling_mean(expected_ranges, 3, 2)
    expected_rv = (None, *reference_rolling_volatility(expected_returns, 3))

    assert_parity(simple_returns(closes), expected_returns)
    assert_parity(true_range(highs, lows, closes), expected_ranges)
    assert_parity(
        average_true_range(highs, lows, closes, window=3, min_periods=2),
        expected_atr,
    )
    assert_parity(
        realized_volatility(closes, window=3, annualization_periods=1),
        expected_rv,
    )


def test_batch_and_prefix_single_observation_calculations_agree() -> None:
    values = [10, 12, 9, 15, 20, 11]
    kernels = (
        lambda items: rolling_mean(items, window=3, min_periods=2),
        lambda items: rolling_volatility(items, window=3, min_periods=2),
        lambda items: rolling_zscore(items, window=3, min_periods=2),
        lambda items: rolling_percentile(items, window=3, min_periods=2),
        lambda items: historical_normalize(items, window=3, min_periods=2),
        lambda items: realized_volatility(
            items,
            window=3,
            min_periods=2,
            annualization_periods=365,
        ),
    )

    for kernel in kernels:
        batch = kernel(values)
        single = np.asarray([kernel(values[: index + 1])[-1] for index in range(len(values))])
        np.testing.assert_allclose(batch, single, equal_nan=True)

    batch_returns = simple_returns(values)
    prefix_returns = np.asarray(
        [simple_returns(values[: index + 1])[-1] for index in range(1, len(values))]
    )
    np.testing.assert_allclose(batch_returns, prefix_returns)


def test_true_range_and_atr_batch_match_prefix_single_observation() -> None:
    high = [12, 13, 12, 15]
    low = [9, 10, 8, 11]
    close = [11, 12, 10, 14]
    batch_ranges = true_range(high, low, close)
    batch_atr = average_true_range(high, low, close, window=2)
    prefix_ranges = []
    prefix_atr = []
    for index in range(len(close)):
        prefix_ranges.append(
            true_range(
                high[: index + 1],
                low[: index + 1],
                close[: index + 1],
            )[-1]
        )
        prefix_atr.append(
            average_true_range(
                high[: index + 1],
                low[: index + 1],
                close[: index + 1],
                window=2,
            )[-1]
        )

    np.testing.assert_allclose(batch_ranges, prefix_ranges)
    np.testing.assert_allclose(batch_atr, prefix_atr, equal_nan=True)


def test_appending_future_observations_never_changes_earlier_outputs() -> None:
    values = [10, 12, 9, 15, 20]
    future = [*values, 1_000_000]
    kernels = (
        lambda items: rolling_mean(items, window=3),
        lambda items: rolling_volatility(items, window=3),
        lambda items: rolling_zscore(items, window=3),
        lambda items: rolling_percentile(items, window=3),
        lambda items: historical_normalize(items, window=3),
        lambda items: realized_volatility(items, window=3),
    )

    for kernel in kernels:
        np.testing.assert_allclose(
            kernel(future)[: len(values)],
            kernel(values),
            equal_nan=True,
        )


def test_missing_values_propagate_or_omit_without_zero_fill() -> None:
    values = [1, np.nan, 3, 4]

    with pytest.raises(NumericInputError, match="NaN"):
        rolling_mean(values, window=2)
    np.testing.assert_allclose(
        rolling_mean(values, window=2, min_periods=1, nan_policy="propagate"),
        [1, np.nan, np.nan, 3.5],
        equal_nan=True,
    )
    np.testing.assert_allclose(
        rolling_mean(values, window=2, min_periods=1, nan_policy="omit"),
        [1, 1, 3, 3.5],
        equal_nan=True,
    )
    assert not np.any(rolling_mean([1, 2], window=3) == 0)


def test_prior_window_statistics_omit_only_missing_history_and_keep_shape() -> None:
    values = [1, np.nan, 3, 4]

    zscores = rolling_zscore(
        values,
        window=3,
        min_periods=2,
        nan_policy="omit",
    )
    percentiles = rolling_percentile(
        values,
        window=3,
        min_periods=1,
        nan_policy="omit",
    )
    normalized = historical_normalize(
        values,
        window=3,
        min_periods=1,
        nan_policy="omit",
    )

    assert zscores.shape == percentiles.shape == normalized.shape == (4,)
    np.testing.assert_allclose(zscores, [np.nan, np.nan, np.nan, 2], equal_nan=True)
    np.testing.assert_allclose(
        percentiles,
        [np.nan, np.nan, 100, 100],
        equal_nan=True,
    )
    np.testing.assert_allclose(
        normalized,
        [np.nan, np.nan, np.nan, 100],
        equal_nan=True,
    )


def test_temporal_kernels_propagate_missing_values_without_dropping_rows() -> None:
    returns = simple_returns([100, np.nan, 110], nan_policy="propagate")
    ranges = true_range(
        [101, np.nan, 112],
        [99, np.nan, 108],
        [100, np.nan, 110],
        nan_policy="propagate",
    )

    assert returns.shape == (2,) and np.isnan(returns).all()
    assert ranges.shape == (3,)
    assert ranges[0] == 2 and np.isnan(ranges[1:]).all()
    with pytest.raises(NumericInputError, match="nan_policy"):
        simple_returns([100, 110], nan_policy="omit")


def test_empty_inputs_and_invalid_parameters_are_explicit() -> None:
    assert rolling_mean([], window=2).shape == (0,)
    assert simple_returns([]).shape == (0,)
    assert true_range([], [], []).shape == (0,)
    assert realized_volatility([], window=2).shape == (0,)

    with pytest.raises(NumericInputError, match="window"):
        rolling_mean([1, 2], window=0)
    with pytest.raises(NumericInputError, match="min_periods"):
        rolling_mean([1, 2], window=2, min_periods=3)
    with pytest.raises(NumericInputError, match="upper"):
        historical_normalize([1, 2], window=1, lower=1, upper=1)
    with pytest.raises(NumericInputError, match="strictly positive"):
        simple_returns([1, 0])
    with pytest.raises(NumericInputError, match="high values"):
        true_range([1], [2], [1.5])
