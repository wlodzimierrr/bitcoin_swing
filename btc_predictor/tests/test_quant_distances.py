from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.quant import (
    NumericInputError,
    atr_normalized_distance,
    cluster_distance_matrix,
    distance_to_resistance,
    distance_to_support,
    entry_distance_score,
    pairwise_price_distance,
)


def test_pairwise_price_distance_supports_scalars_vectors_and_scalar_expansion() -> None:
    assert pairwise_price_distance(100, 93) == 7.0
    np.testing.assert_array_equal(
        pairwise_price_distance([100, 105, 110], [95, 100, 120]),
        [5, 5, 10],
    )
    expanded = pairwise_price_distance(100, np.asarray([[95, 100], [105, 110]]))

    assert expanded.dtype == np.float64
    assert expanded.shape == (2, 2)
    assert expanded.flags.owndata
    np.testing.assert_array_equal(expanded, [[5, 0], [5, 10]])


def test_pairwise_price_distance_rejects_implicit_array_broadcasting() -> None:
    with pytest.raises(NumericInputError, match="identical shapes"):
        pairwise_price_distance([100, 101], [[100, 101]])


def test_atr_normalized_distance_supports_scalar_and_aligned_atr() -> None:
    assert atr_normalized_distance(105, 100, 10) == 0.5
    np.testing.assert_array_equal(
        atr_normalized_distance([105, 110], 100, [10, 5]),
        [0.5, 2.0],
    )


@pytest.mark.parametrize("atr", [None, 0, -1])
def test_atr_normalized_distance_rejects_missing_or_non_positive_atr(atr) -> None:
    with pytest.raises(NumericInputError, match="atr"):
        atr_normalized_distance(105, 100, atr)


def test_atr_nan_is_only_allowed_with_explicit_propagation() -> None:
    with pytest.raises(NumericInputError, match="NaN"):
        atr_normalized_distance([105, 110], 100, [10, np.nan])

    result = atr_normalized_distance(
        [105, 110],
        100,
        [10, np.nan],
        nan_policy="propagate",
    )

    assert result[0] == 0.5
    assert np.isnan(result[1])


def test_extreme_finite_distance_arithmetic_fails_without_returning_infinity() -> None:
    with pytest.raises(NumericInputError, match="finite float64 range"):
        atr_normalized_distance(1e308, 1e-308, 1e-308)
    with pytest.raises(NumericInputError, match="finite float64 range"):
        cluster_distance_matrix([1e-308, 1e308], mode="fractional")


def test_nearest_directional_level_distances_are_deterministic() -> None:
    prices = [100, 115, 125]
    supports = [80, 95, 110]
    resistances = [105, 120, 140]

    np.testing.assert_array_equal(distance_to_support(prices, supports), [5, 5, 15])
    np.testing.assert_array_equal(
        distance_to_resistance(prices, resistances),
        [5, 5, 15],
    )
    np.testing.assert_array_equal(
        distance_to_support(prices, supports, atr=[10, 5, 15]),
        [0.5, 1, 1],
    )


def test_missing_directional_levels_are_explicit_nan_results() -> None:
    no_support = distance_to_support([90, 100], [95])
    no_resistance = distance_to_resistance([100, 110], [105])
    empty = distance_to_support(100, [])

    assert np.isnan(no_support[0])
    assert no_support[1] == 5
    assert no_resistance[0] == 5
    assert np.isnan(no_resistance[1])
    assert np.isnan(empty)


def test_missing_level_input_propagates_to_every_dependent_result() -> None:
    result = distance_to_support(
        [100, 110],
        [95, np.nan],
        nan_policy="propagate",
    )

    assert np.all(np.isnan(result))


def test_cluster_distance_matrix_supports_static_fractional_and_atr_modes() -> None:
    prices = np.asarray([100, 105, 120], dtype=np.float64)

    absolute = cluster_distance_matrix(prices, mode="absolute")
    static = cluster_distance_matrix(prices, mode="static")
    fractional = cluster_distance_matrix(prices, mode="fractional")
    normalized = cluster_distance_matrix(prices, mode="atr", atr=10)

    np.testing.assert_array_equal(absolute, [[0, 5, 20], [5, 0, 15], [20, 15, 0]])
    np.testing.assert_array_equal(static, absolute)
    np.testing.assert_allclose(
        fractional,
        [[0, 0.05, 0.20], [0.05, 0, 15 / 105], [0.20, 15 / 105, 0]],
    )
    np.testing.assert_array_equal(normalized, absolute / 10)
    np.testing.assert_array_equal(cluster_distance_matrix(prices), fractional)
    assert absolute.dtype == np.float64
    assert absolute.flags.c_contiguous


def test_fractional_matrix_reproduces_btc_095_adjacent_distance() -> None:
    prices = [Decimal("95"), Decimal("96"), Decimal("120"), Decimal("122")]
    matrix = cluster_distance_matrix(prices, mode="fractional")

    for index in range(1, len(prices)):
        expected = (prices[index] - prices[index - 1]) / prices[index - 1]
        assert matrix[index - 1, index] == pytest.approx(float(expected), abs=1e-15)


def test_cluster_distance_matrix_is_symmetric_repeatable_and_handles_empty_input() -> None:
    first = cluster_distance_matrix([99, 100, 101])
    second = cluster_distance_matrix([99, 100, 101])
    empty = cluster_distance_matrix([])

    np.testing.assert_array_equal(first, first.T)
    np.testing.assert_array_equal(first, second)
    assert empty.shape == (0, 0)
    assert empty.dtype == np.float64


def test_entry_distance_score_reproduces_existing_fractional_structure_formula() -> None:
    entries = np.asarray([100, 100, 100, 100, 95])
    supports = np.asarray([100, 99, 95, 90, 100])

    scores = entry_distance_score(
        entries,
        supports,
        full_score_distance=0.01,
        zero_score_distance=0.08,
    )

    expected_middle = 100 * (0.08 - 0.05) / (0.08 - 0.01)
    np.testing.assert_allclose(scores, [100, 100, expected_middle, 0, 100])


def test_entry_distance_score_can_express_no_chase_thresholds_in_atr_units() -> None:
    score = entry_distance_score(
        [102.5, 105, 110],
        100,
        mode="atr",
        atr=10,
        full_score_distance=0.25,
        zero_score_distance=1.0,
    )

    np.testing.assert_allclose(score, [100, 100 * (1 - 1 / 3), 0])
    scalar = entry_distance_score(
        105,
        100,
        mode="atr",
        atr=10,
        full_score_distance=0.25,
        zero_score_distance=1.0,
    )
    assert scalar == pytest.approx(score[1])


@pytest.mark.parametrize(
    "call,match",
    [
        (lambda: pairwise_price_distance(0, 100), "positive prices"),
        (lambda: pairwise_price_distance(np.inf, 100), "infinite"),
        (lambda: cluster_distance_matrix([100], mode="unknown"), "mode"),
        (lambda: cluster_distance_matrix([100], mode="atr"), "atr"),
        (lambda: cluster_distance_matrix([100], mode="absolute", atr=10), "only valid"),
        (
            lambda: entry_distance_score(
                100,
                95,
                full_score_distance=0.05,
                zero_score_distance=0.05,
            ),
            "greater than",
        ),
    ],
)
def test_invalid_distance_inputs_fail_fast(call, match) -> None:
    with pytest.raises(NumericInputError, match=match):
        call()


# --- BTC-220: mode/ATR pairing and scalar-parameter contracts -------------


def test_entry_distance_score_requires_atr_when_mode_is_atr() -> None:
    with pytest.raises(NumericInputError, match="atr is required when mode is 'atr'"):
        entry_distance_score(
            [100.0],
            [95.0],
            full_score_distance=0.0,
            zero_score_distance=2.0,
            mode="atr",
        )


def test_entry_distance_score_rejects_atr_outside_atr_mode() -> None:
    with pytest.raises(
        NumericInputError,
        match="atr is only valid when mode is 'atr'",
    ):
        entry_distance_score(
            [100.0],
            [95.0],
            full_score_distance=0.0,
            zero_score_distance=0.05,
            mode="static",
            atr=5.0,
        )


def test_entry_distance_score_rejects_atr_of_a_different_shape() -> None:
    with pytest.raises(
        NumericInputError,
        match="atr must be scalar or have the same shape",
    ):
        entry_distance_score(
            [100.0, 200.0],
            [95.0, 190.0],
            full_score_distance=0.0,
            zero_score_distance=2.0,
            mode="atr",
            atr=[5.0, 6.0, 7.0],
        )


def test_entry_distance_score_requires_an_ordered_score_interval() -> None:
    with pytest.raises(
        NumericInputError,
        match="zero_score_distance must be greater than full_score_distance",
    ):
        entry_distance_score(
            [100.0],
            [95.0],
            full_score_distance=0.05,
            zero_score_distance=0.05,
        )


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"full_score_distance": -0.01}, "full_score_distance must be non-negative"),
        ({"zero_score_distance": 0.0}, "zero_score_distance must be positive"),
        ({"zero_score_distance": -1.0}, "zero_score_distance must be positive"),
    ],
)
def test_entry_distance_score_bounds_its_scalar_parameters(kwargs, match) -> None:
    call = {"full_score_distance": 0.0, "zero_score_distance": 0.05} | kwargs

    with pytest.raises(NumericInputError, match=match):
        entry_distance_score([100.0], [95.0], **call)


@pytest.mark.parametrize(
    "value",
    [True, np.bool_(True)],
)
def test_distance_scalar_parameters_reject_booleans(value) -> None:
    with pytest.raises(NumericInputError, match="must not be boolean"):
        entry_distance_score(
            [100.0],
            [95.0],
            full_score_distance=0.0,
            zero_score_distance=value,
        )


@pytest.mark.parametrize(
    "value",
    [[0.05], np.asarray([0.05]), 1 + 2j, "0.05", np.nan, np.inf, None],
)
def test_distance_scalar_parameters_must_be_finite_float64_scalars(value) -> None:
    with pytest.raises(NumericInputError, match="must be a finite float64 scalar"):
        entry_distance_score(
            [100.0],
            [95.0],
            full_score_distance=0.0,
            zero_score_distance=value,
        )


def test_cluster_distance_matrix_requires_a_positive_atr_in_atr_mode() -> None:
    with pytest.raises(NumericInputError, match="atr must be positive"):
        cluster_distance_matrix([100.0, 105.0], mode="atr", atr=0.0)


def test_cluster_distance_matrix_rejects_atr_outside_atr_mode() -> None:
    with pytest.raises(
        NumericInputError,
        match="atr is only valid when mode is 'atr'",
    ):
        cluster_distance_matrix([100.0, 105.0], mode="static", atr=5.0)


def test_ragged_distance_input_is_rejected_before_coercion() -> None:
    with pytest.raises(NumericInputError, match="regular numeric array"):
        pairwise_price_distance([[100.0, 101.0], [102.0]], 100.0)


def test_price_nan_requires_explicit_propagation() -> None:
    with pytest.raises(NumericInputError, match="NaN"):
        pairwise_price_distance([100, np.nan], 95)

    result = pairwise_price_distance(
        [100, np.nan],
        95,
        nan_policy="propagate",
    )

    assert result[0] == 5
    assert np.isnan(result[1])
