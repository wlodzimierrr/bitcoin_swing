from math import erf, exp, sqrt

import numpy as np
import pytest

from btc_predictor.quant import (
    NumericInputError,
    bounded_linear,
    clip_score,
    exponential_decay,
    gaussian_health,
    normal_cdf_score,
    percentile_to_health,
    sigmoid,
    smooth_penalty,
    winsorize,
)


def test_scalar_and_vector_results_agree_for_elementwise_transforms() -> None:
    values = np.asarray([-2.0, -0.25, 0.0, 0.75, 3.0], dtype=np.float64)
    transforms = (
        lambda item: gaussian_health(item, preferred=0.25, width=1.25),
        lambda item: sigmoid(item, midpoint=0.25, steepness=1.5),
        lambda item: normal_cdf_score(item, mean=0.25, standard_deviation=1.25),
        lambda item: bounded_linear(
            item,
            input_minimum=-2,
            input_maximum=3,
        ),
        lambda item: smooth_penalty(item, threshold=0, width=2),
        lambda item: clip_score(item),
    )

    for transform in transforms:
        vector = transform(values)
        scalar = np.asarray([transform(float(value)) for value in values])
        np.testing.assert_allclose(vector, scalar, rtol=0, atol=1e-12)


def test_scalar_input_returns_float_and_arrays_preserve_shape_and_dtype() -> None:
    source = np.asarray([[0, 1], [2, 3]], dtype=np.int64)

    scalar = sigmoid(0)
    vector = sigmoid(source)

    assert isinstance(scalar, float)
    assert isinstance(vector, np.ndarray)
    assert vector.dtype == np.float64
    assert vector.shape == source.shape
    assert vector.flags.c_contiguous
    assert vector.flags.owndata
    np.testing.assert_array_equal(source, [[0, 1], [2, 3]])


def test_gaussian_health_reproduces_positioning_formula() -> None:
    values = np.asarray([-3.0, -0.5, 0.25, 1.5, 4.0])
    expected = np.asarray(
        [100 * exp(-0.5 * (((value - 0.25) / 1.25) ** 2)) for value in values]
    )

    result = gaussian_health(values, preferred=0.25, width=1.25)

    np.testing.assert_allclose(result, expected, rtol=1e-15, atol=1e-15)
    assert gaussian_health(0.25, preferred=0.25, width=1.25) == 100.0


def test_normal_cdf_score_reproduces_trend_score_conversion() -> None:
    values = np.asarray([-3.0, -0.5, 0.0, 0.525, 3.0])
    expected = np.asarray(
        [100 * (0.5 * (1.0 + erf(value / sqrt(2.0)))) for value in values]
    )

    result = normal_cdf_score(values)

    np.testing.assert_allclose(result, expected, rtol=0, atol=1e-14)
    assert normal_cdf_score(0) == 50.0


def test_sigmoid_is_stable_for_extreme_values_and_supports_reverse_slope() -> None:
    values = np.asarray([-1e308, 0.0, 1e308])

    increasing = sigmoid(values)
    decreasing = sigmoid(values, steepness=-1)

    np.testing.assert_array_equal(increasing, [0.0, 0.5, 1.0])
    np.testing.assert_array_equal(decreasing, [1.0, 0.5, 0.0])


def test_extreme_finite_intervals_are_stable_and_do_not_create_nan() -> None:
    assert bounded_linear(
        0,
        input_minimum=-1e308,
        input_maximum=1e308,
    ) == 50
    assert sigmoid(
        -1e308,
        midpoint=1e308,
        lower=-1e308,
        upper=1e308,
    ) == -1e308
    assert normal_cdf_score(
        -1e308,
        mean=1e308,
        minimum=-1e308,
        maximum=1e308,
    ) == -1e308

    values = bounded_linear(
        [-1e308, 0, 1e308],
        input_minimum=-1e308,
        input_maximum=1e308,
    )
    np.testing.assert_array_equal(values, [0, 50, 100])
    assert np.isfinite(values).all()

    with pytest.raises(NumericInputError, match="finite float64 range"):
        bounded_linear(
            1e308,
            input_minimum=-1,
            input_maximum=1,
            output_minimum=-1e308,
            output_maximum=1e308,
            clip=False,
        )


def test_bounded_linear_clips_by_default_and_can_extrapolate() -> None:
    values = [-5, 0, 5, 10, 15]

    clipped = bounded_linear(values, input_minimum=0, input_maximum=10)
    extrapolated = bounded_linear(
        values,
        input_minimum=0,
        input_maximum=10,
        clip=False,
    )

    np.testing.assert_array_equal(clipped, [0, 0, 50, 100, 100])
    np.testing.assert_array_equal(extrapolated, [-50, 0, 50, 100, 150])


def test_smooth_penalty_has_bounded_cubic_transition_in_both_directions() -> None:
    values = [-1, 0, 0.5, 1, 1.5, 2, 3]

    above = smooth_penalty(values, threshold=0, width=2, maximum=80)
    below = smooth_penalty(values, threshold=2, width=2, maximum=80, direction="below")

    np.testing.assert_allclose(above, [0, 0, 12.5, 40, 67.5, 80, 80])
    np.testing.assert_allclose(below, [80, 80, 67.5, 40, 12.5, 0, 0])


def test_exponential_decay_accepts_non_negative_distances_and_extremes() -> None:
    values = np.asarray([0, 1, 2, 1e308])

    result = exponential_decay(values, initial=100, decay_rate=0.5)

    np.testing.assert_allclose(result[:3], [100, 100 * exp(-0.5), 100 * exp(-1)])
    assert result[3] == 0
    with pytest.raises(NumericInputError, match="non-negative"):
        exponential_decay([-1, 0])


def test_clip_score_and_percentile_health_enforce_score_contracts() -> None:
    np.testing.assert_array_equal(clip_score([-10, 0, 60, 100, 110]), [0, 0, 60, 100, 100])
    np.testing.assert_array_equal(percentile_to_health([0, 25, 100]), [100, 75, 0])
    np.testing.assert_array_equal(
        percentile_to_health([0, 25, 100], higher_is_healthier=True),
        [0, 25, 100],
    )

    with pytest.raises(NumericInputError, match="between 0 and 100"):
        percentile_to_health([-1, 50])


def test_winsorize_uses_linear_quantiles_and_preserves_shape() -> None:
    values = np.asarray([[0.0, 1.0, 2.0], [3.0, 100.0, 200.0]])
    expected_bounds = np.quantile(values, (0.2, 0.8), method="linear")

    result = winsorize(values, lower_quantile=0.2, upper_quantile=0.8)

    np.testing.assert_array_equal(result, np.clip(values, *expected_bounds))
    assert result.shape == values.shape
    assert winsorize(42.0) == 42.0

    np.testing.assert_array_equal(
        winsorize(
            [-1e308, 1e308],
            lower_quantile=0.5,
            upper_quantile=0.5,
        ),
        [0, 0],
    )


@pytest.mark.parametrize(
    "transform",
    [
        gaussian_health,
        sigmoid,
        normal_cdf_score,
        lambda values, **kwargs: bounded_linear(
            values,
            input_minimum=0,
            input_maximum=1,
            **kwargs,
        ),
        lambda values, **kwargs: smooth_penalty(
            values,
            threshold=0,
            width=1,
            **kwargs,
        ),
        exponential_decay,
        clip_score,
        percentile_to_health,
        winsorize,
    ],
)
def test_nan_is_rejected_by_default(transform) -> None:
    with pytest.raises(NumericInputError, match="NaN"):
        transform([0.0, np.nan])


def test_nan_propagation_is_explicit_and_dependency_aware() -> None:
    elementwise = gaussian_health([0.0, np.nan, 1.0], nan_policy="propagate")
    global_transform = winsorize([0.0, np.nan, 100.0], nan_policy="propagate")

    assert elementwise[0] == 100
    assert np.isnan(elementwise[1])
    assert np.isfinite(elementwise[2])
    assert np.all(np.isnan(global_transform))


@pytest.mark.parametrize(
    "call,match",
    [
        (lambda: gaussian_health(0, width=0), "width"),
        (lambda: normal_cdf_score(0, standard_deviation=0), "standard_deviation"),
        (
            lambda: bounded_linear(0, input_minimum=1, input_maximum=1),
            "input_maximum",
        ),
        (lambda: smooth_penalty(0, threshold=0, width=0), "width"),
        (lambda: sigmoid(0, steepness=0), "steepness"),
        (lambda: clip_score(0, minimum=1, maximum=1), "maximum"),
    ],
)
def test_zero_width_and_degenerate_intervals_fail_fast(call, match) -> None:
    with pytest.raises(NumericInputError, match=match):
        call()


@pytest.mark.parametrize(
    "call,match",
    [
        (lambda: gaussian_health([np.inf]), "infinite"),
        (lambda: sigmoid(True), "boolean"),
        (lambda: bounded_linear(0, input_minimum=0, input_maximum=1, clip=1), "boolean"),
        (lambda: smooth_penalty(0, threshold=0, width=1, direction="sideways"), "direction"),
        (lambda: exponential_decay(0, decay_rate=-1), "decay_rate"),
        (lambda: winsorize([1, 2], lower_quantile=0.8, upper_quantile=0.2), "<="),
        (lambda: winsorize([], lower_quantile=0.1, upper_quantile=0.9), "one observation"),
    ],
)
def test_invalid_inputs_and_parameters_fail_fast(call, match) -> None:
    with pytest.raises(NumericInputError, match=match):
        call()


# --- BTC-220: scalar-parameter and input-shape contracts -----------------
# Every transform funnels its keyword parameters through one ``_finite_scalar``
# guard, so the rejected representations are pinned once here.


@pytest.mark.parametrize(
    "midpoint",
    [True, np.bool_(False)],
)
def test_transform_scalar_parameters_reject_booleans(midpoint) -> None:
    with pytest.raises(NumericInputError, match="must not be boolean"):
        sigmoid(0.0, midpoint=midpoint)


@pytest.mark.parametrize(
    "midpoint",
    [
        [1.0, 2.0],
        np.asarray([1.0]),
        1 + 2j,
        "1.0",
        np.str_("1.0"),
        np.nan,
        np.inf,
        None,
        10**400,
    ],
)
def test_transform_scalar_parameters_must_be_finite_float64_scalars(
    midpoint,
) -> None:
    with pytest.raises(NumericInputError, match="must be a finite float64 scalar"):
        sigmoid(0.0, midpoint=midpoint)


@pytest.mark.parametrize("quantile", [-0.1, 1.1])
def test_winsorize_quantiles_must_be_probabilities(quantile: float) -> None:
    with pytest.raises(NumericInputError, match="must be between 0 and 1"):
        winsorize([1.0, 2.0], lower_quantile=quantile)


def test_ragged_transform_input_is_rejected_before_coercion() -> None:
    with pytest.raises(NumericInputError, match="regular numeric array"):
        sigmoid([[1.0, 2.0], [3.0]])


def test_percentile_to_health_rejects_percentiles_outside_the_domain() -> None:
    with pytest.raises(NumericInputError, match="between 0 and 100"):
        percentile_to_health([-0.5])
    with pytest.raises(NumericInputError, match="between 0 and 100"):
        percentile_to_health([100.5])


def test_empty_arrays_are_supported_only_for_elementwise_transforms() -> None:
    result = normal_cdf_score(np.asarray([], dtype=np.float64))

    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float64
    assert result.shape == (0,)
